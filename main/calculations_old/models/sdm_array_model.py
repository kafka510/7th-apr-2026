"""
Single Diode Model Array implementation using physics-based SDM

This module implements a more accurate SDM model that:
1. Fits SDM parameters (Iph, I0, Rs, Rsh, n) from datasheet values once
2. Reuses those fitted parameters for all subsequent calculations
3. Uses proper IV curve solving and MPP finding algorithms
"""
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from datetime import datetime, date
import time
import logging
from dataclasses import dataclass
from scipy.optimize import least_squares
from django.utils import timezone as django_timezone

from .base_model import BasePowerModel, PowerModelInput, PowerModelOutput

logger = logging.getLogger(__name__)

# Import Django model for saving parameters
try:
    from main.models import PowerModelParametersHistory, AssetList
except ImportError:
    # Handle case where model might not be imported yet
    PowerModelParametersHistory = None
    AssetList = None

# Physical constants
k = 1.380649e-23
q = 1.602176634e-19


@dataclass
class ModuleDS:
    """Module datasheet parameters"""
    Isc: float      # A (module, STC)
    Voc: float      # V (module, STC)
    Imp: float      # A (module, STC)
    Vmp: float      # V (module, STC)
    Ns: int         # series cells per module
    Eg_eV: float    # eV (Si ~1.12)
    alpha_I: float  # A/°C (module Isc temp coeff)
    beta_V: float   # 1/°C (module Voc temp coeff, fraction per °C)


@dataclass
class ArrayConfig:
    """Array configuration"""
    Nser: int       # modules in series per string
    Npar: int       # strings in parallel
    NOCT: float     # °C (use NMOT if that's what you have)


@dataclass
class Derates:
    """DC derating factors"""
    soiling: float = 0.02        # 2% loss
    mismatch: float = 0.02       # module mismatch
    dc_ohmic: float = 0.01       # wiring
    degradation: float = 0.00    # long-term degradation
    availability: float = 0.00   # downtime
    others: float = 0.00         # spectral/AOI etc.

    @property
    def dc_factor(self) -> float:
        # multiplicative derates
        total_loss = 1 - np.prod([1 - x for x in
                                  [self.soiling, self.mismatch, self.dc_ohmic,
                                   self.degradation, self.availability, self.others]])
        return 1 - total_loss


# ===================== Thermal model (Faiman) =====================

def faiman_Tcell(G, Tamb_C, wind_ms, NOCT):
    """Calculate cell temperature using Faiman model"""
    U_sum = 800.0 / max(NOCT - 20.0, 1e-6)   # W/m2-K
    U0, U1 = 0.8 * U_sum, 0.2 * U_sum
    return Tamb_C + G / (U0 + U1 * max(wind_ms, 5.0))


# ===================== SDM primitives =====================

def Vt_Ns(T_K, Ns):
    """Thermal voltage scaled by Ns (module)"""
    return (k * T_K / q) * Ns


def iv_current(V, Iph, I0, Rs, Rsh, n, Vt):
    """Solve I implicitly with Newton (few iterations, robust)"""
    I = max(Iph - V / max(Rsh, 1e-9), 0.0)
    for _ in range(60):
        ea = (V + I*Rs) / (n*Vt)
        ea = np.clip(ea, -60, 60)
        e = np.exp(ea)
        f  = I - Iph + I0*(e - 1) + (V + I*Rs)/Rsh
        df = 1 + I0*e*(Rs/(n*Vt)) + (Rs/Rsh)
        dI = f / max(df, 1e-16)
        I_new = I - np.clip(dI, -2.0, 2.0)
        if abs(I_new - I) < 1e-10:
            I = I_new
            break
        I = I_new
    return max(I, 0.0)


def dIdV(V, I, I0, Rs, Rsh, n, Vt):
    """Calculate dI/dV"""
    ea = (V + I*Rs)/(n*Vt)
    ea = np.clip(ea, -60, 60)
    e = np.exp(ea)
    A = I0*e/(n*Vt) + 1.0/Rsh
    B = 1.0 + Rs*A
    return -A/max(B, 1e-16)


def _f_partials(V, I, I0, Rs, Rsh, n, Vt):
    """
    Partial derivatives of the implicit IV residual f(V,I)=0.
    f = I - Iph + I0*(exp(a)-1) + (V+I*Rs)/Rsh,  a = (V+I*Rs)/(n*Vt).
    Returns (f_V, f_I, f_VV, f_VI, f_II) for use in MPP Newton.
    """
    nVt = n * Vt
    ea = (V + I*Rs) / nVt
    ea = np.clip(ea, -60, 60)
    e = np.exp(ea)
    # f_V = I0*e/(n*Vt) + 1/Rsh,  f_I = 1 + I0*e*Rs/(n*Vt) + Rs/Rsh
    f_V = I0*e/nVt + 1.0/max(Rsh, 1e-9)
    f_I = 1.0 + I0*e*Rs/nVt + Rs/max(Rsh, 1e-9)
    # Second derivatives: f_VV, f_VI, f_II (da/dV=1/nVt, da/dI=Rs/nVt)
    scale = I0*e / (nVt*nVt)
    f_VV = scale
    f_VI = scale * Rs
    f_II = scale * Rs * Rs
    return f_V, f_I, f_VV, f_VI, f_II


# MPP condition: dP/dV = I + V*dI/dV = 0. With f(V,I)=0 we have dI/dV = -f_V/f_I.
# So at MPP: g(V) = I - V*f_V/f_I = 0. Newton on g(V): V_new = V - g(V)/g'(V).

def mpp_newton(Iph, I0, Rs, Rsh, n, Vt, max_outer=15, tol=1e-9):
    """
    Find MPP by Newton on g(V)=I - V*f_V/f_I = 0 (no golden-section, no voltage sweep).
    At each outer iteration: one Newton solve for I(V), then f_V, f_I and second
    derivatives; typically converges in 2-4 outer iterations.
    Returns (Vmp, Imp, Pmp). Falls back to mpp_golden if Newton fails.
    """
    # Initial V guess: ~0.8 * ideal Voc (no full bisection)
    Voc_approx = n*Vt*np.log(1.0 + max(Iph, 1e-30)/max(I0, 1e-30))
    V = 0.8 * min(Voc_approx, 1000.0)  # cap for safety
    V = max(V, 1e-6)

    for _ in range(max_outer):
        # Inner: solve f(V,I)=0 for I (Newton on I)
        I = iv_current(V, Iph, I0, Rs, Rsh, n, Vt)
        I = max(I, 0.0)

        f_V, f_I, f_VV, f_VI, f_II = _f_partials(V, I, I0, Rs, Rsh, n, Vt)
        f_I = max(f_I, 1e-16)

        # g(V) = I - V*f_V/f_I = 0 at MPP
        ratio = f_V / f_I
        g = I - V * ratio

        if abs(g) < tol:
            Vmp = V
            Imp = iv_current(Vmp, Iph, I0, Rs, Rsh, n, Vt)
            return Vmp, max(Imp, 0.0), Vmp * max(Imp, 0.0)

        # g'(V) = dI/dV - ratio - V * (ratio)'
        # dI/dV = -f_V/f_I = -ratio
        # (f_V/f_I)' = (f_VV*f_I^2 - 2*f_V*f_VI*f_I + f_V^2*f_II) / f_I^3
        ratio_prime = (f_VV*f_I*f_I - 2*f_V*f_VI*f_I + f_V*f_V*f_II) / (f_I*f_I*f_I)
        g_prime = -2.0 * ratio - V * ratio_prime
        g_prime = max(abs(g_prime), 1e-16) * (1.0 if g_prime >= 0 else -1.0)

        dV = -g / g_prime
        dV = np.clip(dV, -0.5*V, 0.5*V)  # limit step
        V_new = V + dV
        if V_new <= 0:
            V_new = 0.5 * V
        if V_new >= Voc_approx * 1.01:
            V_new = 0.99 * Voc_approx
        V = V_new

    # Newton did not converge; fall back to golden-section
    return mpp_golden(Iph, I0, Rs, Rsh, n, Vt)


# ===================== Fit SDM from datasheet (STC) =====================

def fit_sdm_from_STC(ds: ModuleDS, Tcell_C=25.0) -> Dict[str, float]:
    """Fit SDM parameters from datasheet STC values"""
    T_K = Tcell_C + 273.15
    Vt = Vt_Ns(T_K, ds.Ns)
    Isc, Voc, Imp, Vmp = ds.Isc, ds.Voc, ds.Imp, ds.Vmp

    # theta = [Iph, log10(I0), Rs, Rsh, n]; bounds are important
    lb = np.array([0.98*Isc, -40, 1e-4, 10.0, 1.0])
    ub = np.array([1.02*Isc,  -2,  2.0, 5000.0, 2.5])

    def residuals(theta):
        Iph, logI0, Rs, Rsh, n = theta
        I0 = 10**logI0
        I0 = max(I0, 1e-30)

        I_0   = iv_current(0.0, Iph, I0, Rs, Rsh, n, Vt)          # = Isc
        I_Voc = iv_current(Voc, Iph, I0, Rs, Rsh, n, Vt)          # = 0
        I_Vmp = iv_current(Vmp, Iph, I0, Rs, Rsh, n, Vt)          # = Imp
        dVmp  = dIdV(Vmp, I_Vmp, I0, Rs, Rsh, n, Vt)              # MPP slope
        mpp_eq = I_Vmp + Vmp * dVmp                               # = 0

        return np.array([
            I_0 - Isc,
            I_Voc - 0.0,
            I_Vmp - Imp,
            mpp_eq,
            (Iph - Isc)           # soft tie Iph≈Isc
        ])

    # seeds
    seeds = []
    for rs in [0.1, 0.3, 0.6]:
        for rsh in [200, 500, 1000]:
            for n in [1.15, 1.3, 1.5]:
                I0_guess = Isc / (np.exp(Voc/(n*Vt)) - 1 + 1e-30)
                seeds.append(np.array([Isc, np.log10(max(I0_guess,1e-30)), rs, rsh, n]))

    best = None
    best_cost = 1e99
    for theta0 in seeds:
        theta0 = np.clip(theta0, lb, ub)
        res = least_squares(residuals, theta0, bounds=(lb, ub),
                            loss='soft_l1', f_scale=0.1, xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=3000)
        if res.success and res.cost < best_cost:
            best = res
            best_cost = res.cost
    if best is None:
        raise RuntimeError("SDM fit failed")

    Iph, logI0, Rs, Rsh, n = best.x
    return {"Iph": Iph, "I0": 10**logI0, "Rs": Rs, "Rsh": Rsh, "n": n, "Vt_ref": Vt, "Tref_C": Tcell_C}


# ===================== Fast MPP solver =====================

def voc_bisect(Iph, I0, Rs, Rsh, n, Vt):
    """Robust Voc via bisection"""
    def I_of_V(V):
        return iv_current(V, Iph, I0, Rs, Rsh, n, Vt)

    # good upper guess from ideal diode (ignore Rs/Rsh)
    Voc_guess = n*Vt*np.log(1.0 + max(Iph,1e-30)/max(I0,1e-30))
    lo, hi = 0.0, max(Voc_guess, 1e-6)

    # ensure I(lo)>0 and I(hi)≈0 or <0; expand hi if needed
    Ilo = I_of_V(lo)
    Ihi = I_of_V(hi)
    tries = 0
    while Ihi > 0.0 and tries < 40:
        hi *= 1.25
        Ihi = I_of_V(hi)
        tries += 1

    # bisection
    for _ in range(80):
        mid = 0.5*(lo+hi)
        Imid = I_of_V(mid)
        if Imid > 0.0:
            lo = mid
        else:
            hi = mid
        if abs(hi-lo) < 1e-7:
            break
    return 0.5*(lo+hi)


def mpp_golden(Iph, I0, Rs, Rsh, n, Vt):
    """Robust MPP via golden-section on P(V)"""
    def I_of_V(V):
        return iv_current(V, Iph, I0, Rs, Rsh, n, Vt)
    def P_of_V(V):
        return V * I_of_V(V)

    Voc = voc_bisect(Iph, I0, Rs, Rsh, n, Vt)
    a, b = 0.0, 0.999*Voc  # search bracket
    gr = (np.sqrt(5) - 1) / 2  # golden ratio (conjugate)
    c = b - gr*(b-a)
    d = a + gr*(b-a)
    Pc, Pd = P_of_V(c), P_of_V(d)

    for _ in range(100):
        if Pc < Pd:
            a = c
            c = d
            Pc = Pd
            d = a + gr*(b-a)
            Pd = P_of_V(d)
        else:
            b = d
            d = c
            Pd = Pc
            c = b - gr*(b-a)
            Pc = P_of_V(c)
        if abs(b-a) < 1e-6:
            break

    Vmp = 0.5*(a+b)
    Imp = I_of_V(Vmp)
    Pmp = Vmp*Imp
    return Vmp, Imp, Pmp


# ===================== Real-time estimator =====================

def estimate_power(G_poa, Tamb_C, wind_ms,
                   ds: ModuleDS, arr: ArrayConfig, der: Derates,
                   fitted: Dict[str, float]) -> Dict[str, float]:
    """Estimate power output using fitted SDM parameters"""
    # 1) cell temperature from POA, ambient, wind
    Tcell_C = faiman_Tcell(G_poa, Tamb_C, wind_ms, arr.NOCT)
    T = Tcell_C + 273.15
    Tref = fitted["Tref_C"] + 273.15

    # 2) update thermal terms
    Vt = Vt_Ns(T, ds.Ns)
    n  = fitted["n"]
    I0_ref = fitted["I0"]
    I0 = I0_ref * (T/Tref)**3 * np.exp((q*ds.Eg_eV/(n*k))*(1/Tref - 1/T))

    # 3) photocurrent at (G,T)
    Iph = (ds.Isc + ds.alpha_I * (Tcell_C - 25.0)) * (G_poa/1000.0)

    # 4) MPP (module): direct Newton on g(V)=0 (no golden-section / voltage sweep)
    Vmp_mod, Imp_mod, Pmp_mod = mpp_newton(Iph, I0, fitted["Rs"], fitted["Rsh"], n, Vt)

    # 5) Scale to string/array
    Vmp_str = arr.Nser * Vmp_mod
    Imp_str = Imp_mod
    Pmp_str = Vmp_str * Imp_str

    Vmp_arr = Vmp_str
    Imp_arr = arr.Npar * Imp_str
    Pdc_raw = Vmp_arr * Imp_arr

    # 6) Apply DC derates
    Pdc = Pdc_raw * der.dc_factor

    return {
        "Tcell_C": Tcell_C,
        "Vmp_module": Vmp_mod, "Imp_module": Imp_mod, "Pmp_module_W": Pmp_mod,
        "Vmp_string": Vmp_str, "Imp_string": Imp_str, "Pmp_string_W": Pmp_str,
        "Pdc_W": Pdc,
        "dc_derate_factor": der.dc_factor
    }


class SDMArrayPowerModel(BasePowerModel):
    """
    Single Diode Model Array implementation
    
    This model:
    1. Fits SDM parameters (Iph, I0, Rs, Rsh, n) from datasheet values once
    2. Caches and reuses those parameters for all subsequent calculations
    3. Uses proper IV curve solving and MPP finding algorithms
    
    This is more accurate than the simplified SDM model as it properly
    solves the single diode equation rather than using approximations.
    """
    
    # Model metadata
    MODEL_CODE = 'sdm_array_v1'
    MODEL_NAME = 'Single Diode Model Array'
    MODEL_VERSION = '1.0.0'
    MODEL_TYPE = 'physics_based'
    
    # Model capabilities
    REQUIRES_WEATHER_DATA = True
    REQUIRES_MODULE_DATASHEET = True
    REQUIRES_HISTORICAL_DATA = False
    SUPPORTS_DEGRADATION = True
    SUPPORTS_SOILING = True
    SUPPORTS_BIFACIAL = False
    SUPPORTS_SHADING = True
    
    # Class-level caches to persist across instances
    _class_parameter_cache: Dict[str, Dict[str, float]] = {}
    _class_module_ds_cache: Dict[str, ModuleDS] = {}
    _class_logged_loaded_params: set = set()
    _class_logged_fitted_params: set = set()
    _class_saved_params: set = set()  # Track which devices have been saved to DB in this session
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize model with parameter cache"""
        super().__init__(config)
        # Use class-level caches to persist across instances
        # Cache for fitted SDM parameters per device
        # Key: device_id, Value: fitted parameters dict
        self._parameter_cache = SDMArrayPowerModel._class_parameter_cache
        # Cache for ModuleDS objects per device
        self._module_ds_cache = SDMArrayPowerModel._class_module_ds_cache
    
    def _get_module_ds(self, module, device) -> ModuleDS:
        """
        Convert module datasheet to ModuleDS dataclass
        
        Args:
            module: PVModuleDatasheet instance
            device: device_list instance
            
        Returns:
            ModuleDS dataclass instance
        """
        # Check cache first
        cache_key = f"{device.device_id}_{module.id if hasattr(module, 'id') else 'default'}"
        if cache_key in self._module_ds_cache:
            return self._module_ds_cache[cache_key]
        
        # Get cells per module (estimate if not available)
        Ns = getattr(module, 'cells_per_module', None)
        if Ns is None or Ns == 0:
            # Estimate from Voc: typically ~0.6V per cell
            Ns = int(round(module.voc_stc / 0.6))
            if Ns < 36:
                Ns = 72  # Default to 72 cells
            logger.debug(f"Estimated cells_per_module={Ns} for device {device.device_id}")
        
        # Get bandgap (default to Si = 1.12 eV)
        Eg_eV = getattr(module, 'bandgap_ev', None) or 1.12
        
        # Get temperature coefficients
        # alpha_I: current temp coeff (A/°C)
        if module.temp_coeff_type_isc == 'absolute':
            alpha_I = module.temp_coeff_isc
        else:
            # Percentage: convert to absolute (A/°C)
            alpha_I = (module.temp_coeff_isc / 100) * module.isc_stc
        
        # beta_V: voltage temp coeff (fraction per °C, not %)
        if module.temp_coeff_type_voc == 'absolute':
            # Convert absolute (V/°C) to fraction per °C
            beta_V = module.temp_coeff_voc / module.voc_stc
        else:
            # Percentage: convert to fraction per °C
            beta_V = module.temp_coeff_voc / 100
        
        module_ds = ModuleDS(
            Isc=module.isc_stc,
            Voc=module.voc_stc,
            Imp=module.imp_stc,
            Vmp=module.vmp_stc,
            Ns=Ns,
            Eg_eV=Eg_eV,
            alpha_I=alpha_I,
            beta_V=beta_V
        )
        
        # Cache it
        self._module_ds_cache[cache_key] = module_ds
        return module_ds
    
    def _get_fitted_parameters(
        self, 
        device, 
        module_ds: ModuleDS,
        save_to_db: bool = True,
        timings_out: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Get fitted SDM parameters for device (cached, or from database, or fit new)
        
        Priority:
        1. Check in-memory cache
        2. Check database for existing parameters
        3. Fit new parameters from datasheet
        
        Args:
            device: device_list instance
            module_ds: ModuleDS dataclass
            save_to_db: Whether to save parameters to database
            timings_out: Optional dict to record per-step times (ms): param_cache_ms,
                        param_db_read_ms, param_fit_sdm_ms, param_db_write_ms
            
        Returns:
            Dictionary with fitted parameters
        """
        def _set_timing(key: str, ms: float) -> None:
            if timings_out is not None:
                timings_out[key] = ms

        # Check cache first
        t0 = time.perf_counter()
        if device.device_id in self._parameter_cache:
            fitted = self._parameter_cache[device.device_id]
            _set_timing('param_cache_ms', (time.perf_counter() - t0) * 1000)
            _set_timing('param_db_read_ms', 0.0)
            _set_timing('param_fit_sdm_ms', 0.0)
            _set_timing('param_db_write_ms', 0.0)
            return fitted

        _set_timing('param_cache_ms', 0.0)

        # Try to fetch from database
        db_read_start = time.perf_counter()
        if PowerModelParametersHistory is not None:
            try:
                # Get module datasheet ID if available
                module_datasheet_id = None
                if hasattr(device, 'module_datasheet_id'):
                    module_datasheet_id = device.module_datasheet_id
                
                # Try to get latest parameters from database
                db_params = self.get_latest_parameters(
                    device_id=device.device_id,
                    module_datasheet_id=module_datasheet_id,
                    model_code=self.MODEL_CODE,
                    parameter_type='datasheet'
                )
                _set_timing('param_db_read_ms', (time.perf_counter() - db_read_start) * 1000)

                if db_params and 'parameters' in db_params:
                    # Extract parameters from database record
                    params_json = db_params['parameters']
                    if isinstance(params_json, dict):
                        # Convert to the format expected by the model
                        fitted = {
                            'Iph': params_json.get('Iph'),
                            'I0': params_json.get('I0'),
                            'Rs': params_json.get('Rs'),
                            'Rsh': params_json.get('Rsh'),
                            'n': params_json.get('n'),
                            'Vt_ref': params_json.get('Vt_ref'),
                            'Tref_C': params_json.get('Tref_C', 25.0),
                        }
                        
                        # Validate that all required parameters are present
                        if all(v is not None for v in fitted.values()):
                            # Cache it
                            self._parameter_cache[device.device_id] = fitted
                            _set_timing('param_fit_sdm_ms', 0.0)
                            _set_timing('param_db_write_ms', 0.0)
                            # Only log once per device (use class-level cache)
                            device_key = f"{device.device_id}:{self.MODEL_CODE}"
                            if device_key not in SDMArrayPowerModel._class_logged_loaded_params:
                                logger.info(f"Loaded SDM parameters from database for device {device.device_id}: "
                                           f"Rs={fitted['Rs']:.4f}Ohm, Rsh={fitted['Rsh']:.2f}Ohm, n={fitted['n']:.3f}")
                                SDMArrayPowerModel._class_logged_loaded_params.add(device_key)
                            # Parameters loaded from DB are already saved, no need to save again
                            return fitted
                        else:
                            logger.warning(f"Incomplete parameters in database for device {device.device_id}, will refit")
            except Exception as e:
                _set_timing('param_db_read_ms', (time.perf_counter() - db_read_start) * 1000)
                logger.warning(f"Error fetching parameters from database for device {device.device_id}: {str(e)}, will refit")
        else:
            _set_timing('param_db_read_ms', 0.0)
        
        # If not found in cache or database, fit parameters from datasheet
        logger.info(f"Fitting new SDM parameters from datasheet for device {device.device_id}")
        try:
            fit_start = time.perf_counter()
            fitted = fit_sdm_from_STC(module_ds, Tcell_C=25.0)
            _set_timing('param_fit_sdm_ms', (time.perf_counter() - fit_start) * 1000)
            # Cache it
            self._parameter_cache[device.device_id] = fitted
            # Only log once per device (use class-level cache)
            device_key = f"{device.device_id}:{self.MODEL_CODE}"
            if device_key not in SDMArrayPowerModel._class_logged_fitted_params:
                logger.info(f"Successfully fitted SDM parameters for device {device.device_id}: "
                           f"Rs={fitted['Rs']:.4f}Ohm, Rsh={fitted['Rsh']:.2f}Ohm, n={fitted['n']:.3f}")
                SDMArrayPowerModel._class_logged_fitted_params.add(device_key)
            
            # Save to database if enabled
            if save_to_db and PowerModelParametersHistory is not None:
                write_start = time.perf_counter()
                self._save_parameters_to_db(device, module_ds, fitted)
                _set_timing('param_db_write_ms', (time.perf_counter() - write_start) * 1000)
            else:
                _set_timing('param_db_write_ms', 0.0)
            
            return fitted
        except Exception as e:
            logger.error(f"Failed to fit SDM parameters for device {device.device_id}: {str(e)}")
            raise
    
    def _save_parameters_to_db(
        self,
        device,
        module_ds: ModuleDS,
        fitted: Dict[str, float]
    ):
        """
        Save fitted SDM parameters to database
        
        Args:
            device: device_list instance
            module_ds: ModuleDS dataclass
            fitted: Fitted parameters dictionary
        """
        try:
            if PowerModelParametersHistory is None:
                logger.warning("PowerModelParametersHistory model not available")
                return
            
            # Get asset code and timezone
            asset_code = device.parent_code
            timezone_str = None
            
            # Get timezone from asset
            if asset_code and AssetList is not None:
                try:
                    asset = AssetList.objects.get(asset_code=asset_code)
                    timezone_str = asset.timezone
                except AssetList.DoesNotExist:
                    logger.warning(f"Asset {asset_code} not found, using UTC timezone")
                    timezone_str = "+00:00"
                except Exception as e:
                    logger.warning(f"Error getting asset timezone: {str(e)}, using UTC")
                    timezone_str = "+00:00"
            
            if timezone_str is None:
                timezone_str = "+00:00"  # Default to UTC
            
            # Get module datasheet ID if available
            module_datasheet_id = None
            if hasattr(device, 'module_datasheet_id'):
                module_datasheet_id = device.module_datasheet_id
            
            # Prepare parameters as JSON
            parameters_json = {
                'Iph': fitted['Iph'],
                'I0': fitted['I0'],
                'Rs': fitted['Rs'],
                'Rsh': fitted['Rsh'],
                'n': fitted['n'],
                'Vt_ref': fitted['Vt_ref'],
                'Tref_C': fitted['Tref_C'],
            }
            
            # Check if parameters already exist for this device and model
            existing = PowerModelParametersHistory.objects.filter(
                model_code=self.MODEL_CODE,
                model_version=self.MODEL_VERSION,
                parameter_type='datasheet',
                device_id=device.device_id,
            ).first()
            
            if existing:
                # Update existing record with new parameters and timestamp
                existing.parameters = parameters_json
                existing.calculated_at = django_timezone.now()
                existing.timezone = timezone_str
                existing.module_datasheet_id = module_datasheet_id
                existing.asset_code = asset_code or ''
                existing.metadata = {
                    'module_model': getattr(device.get_module_datasheet(), 'module_model', None),
                    'modules_in_series': device.modules_in_series,
                    'strings_in_parallel': getattr(device, 'strings_in_parallel', None),
                }
                existing.save()
                # Only log once per device (use class-level cache)
                device_save_key = f"{device.device_id}:{self.MODEL_CODE}"
                if device_save_key not in SDMArrayPowerModel._class_saved_params:
                    logger.info(f"Updated SDM parameters in database for device {device.device_id}")
                    SDMArrayPowerModel._class_saved_params.add(device_save_key)
            else:
                # Create new database record
                # These are datasheet-based parameters (calculated from module datasheet)
                PowerModelParametersHistory.objects.create(
                    model_code=self.MODEL_CODE,
                    model_version=self.MODEL_VERSION,
                    parameter_type='datasheet',  # SDM parameters are derived from datasheet
                    module_datasheet_id=module_datasheet_id,
                    device_id=device.device_id,  # Also store device_id for reference
                    asset_code=asset_code or '',
                    parameters=parameters_json,
                    calculated_at=django_timezone.now(),
                    timezone=timezone_str,
                    fit_method='least_squares',  # SDM uses least squares fitting
                    metadata={
                        'module_model': getattr(device.get_module_datasheet(), 'module_model', None),
                        'modules_in_series': device.modules_in_series,
                        'strings_in_parallel': getattr(device, 'strings_in_parallel', None),
                    }
                )
                # Only log once per device (use class-level cache)
                device_save_key = f"{device.device_id}:{self.MODEL_CODE}"
                if device_save_key not in SDMArrayPowerModel._class_saved_params:
                    logger.info(f"Saved new SDM parameters to database for device {device.device_id}")
                    SDMArrayPowerModel._class_saved_params.add(device_save_key)
            
        except Exception as e:
            # Don't fail the calculation if database save fails
            logger.error(f"Failed to save SDM parameters to database for device {device.device_id}: {str(e)}", exc_info=True)
    
    def calculate_expected_power(
        self,
        input_data: PowerModelInput
    ) -> PowerModelOutput:
        """
        Calculate expected power using SDM Array model
        
        Args:
            input_data: StandardizedInput data
            
        Returns:
            PowerModelOutput with expected power and detailed breakdown
        """
        start_time = time.time()
        timings_ms: Dict[str, float] = {}

        # Validate device has module datasheet
        device = input_data.device
        module = device.get_module_datasheet()
        if not module:
            raise ValueError(
                f"Device {device.device_id} has no module datasheet configured"
            )
        
        # Get weather inputs
        irradiance = input_data.irradiance
        ambient_temp = input_data.ambient_temp
        module_temp = input_data.module_temp
        wind_speed = input_data.wind_speed or 0.0
        
        # Estimate module temperature if not provided
        if module_temp is None:
            if ambient_temp is None:
                raise ValueError(
                    "Either module_temp or ambient_temp must be provided"
                )
            # Use NOCT from module or default
            noct = getattr(module, 'noct', None) or 45.0
            module_temp = faiman_Tcell(irradiance, ambient_temp, wind_speed, noct)
        
        # Get ModuleDS object
        t0 = time.perf_counter()
        module_ds = self._get_module_ds(module, device)
        timings_ms['get_module_ds_ms'] = (time.perf_counter() - t0) * 1000

        # Get fitted parameters (cached, and save to DB if new)
        t0 = time.perf_counter()
        fitted = self._get_fitted_parameters(device, module_ds, save_to_db=True, timings_out=timings_ms)
        timings_ms['get_fitted_parameters_ms'] = (time.perf_counter() - t0) * 1000

        # Create array config
        arr = ArrayConfig(
            Nser=device.modules_in_series or 1,
            Npar=getattr(device, 'strings_in_parallel', None) or 1,
            NOCT=getattr(module, 'noct', None) or 45.0
        )
        
        # Create derates
        soiling_loss = (device.expected_soiling_loss or 0) / 100
        shading_loss = (device.shading_factor or 0) / 100
        degradation_pct = self._calculate_degradation_pct(device)
        degradation_loss = degradation_pct / 100
        
        der = Derates(
            soiling=soiling_loss,
            mismatch=0.02,  # Default 2% mismatch
            dc_ohmic=0.01,  # Default 1% wiring loss
            degradation=degradation_loss,
            availability=0.00,
            others=0.00
        )
        
        # Estimate power (Vmpp / MPP calculation)
        t0 = time.perf_counter()
        result = estimate_power(
            G_poa=irradiance,
            Tamb_C=ambient_temp if ambient_temp is not None else module_temp - 20,
            wind_ms=wind_speed,
            ds=module_ds,
            arr=arr,
            der=der,
            fitted=fitted
        )
        timings_ms['estimate_power_vmpp_ms'] = (time.perf_counter() - t0) * 1000

        # Calculate execution time and other (so breakdown sums to total)
        execution_time_ms = (time.time() - start_time) * 1000
        timings_ms['total_ms'] = execution_time_ms
        timed_sum = (
            timings_ms.get('get_module_ds_ms', 0)
            + timings_ms.get('get_fitted_parameters_ms', 0)
            + timings_ms.get('estimate_power_vmpp_ms', 0)
        )
        timings_ms['other_ms'] = max(0.0, execution_time_ms - timed_sum)

        # Return standardized output
        return PowerModelOutput(
            expected_power=result['Pdc_W'],
            expected_voltage=result['Vmp_string'],
            expected_current=result['Imp_string'],
            degradation_factor=1 - degradation_loss,
            soiling_factor=1 - soiling_loss,
            temperature_factor=None,  # Temperature effect is in the SDM calculation
            low_irradiance_factor=None,  # Handled in SDM
            shading_factor=1 - shading_loss,
            model_code=self.MODEL_CODE,
            model_version=self.MODEL_VERSION,
            confidence=1.0,  # Physics-based model always has 100% confidence
            execution_time_ms=execution_time_ms,
            details={
                'module_temp': result['Tcell_C'],
                'Vmp_module': result['Vmp_module'],
                'Imp_module': result['Imp_module'],
                'Pmp_module_W': result['Pmp_module_W'],
                'Pmp_string_W': result['Pmp_string_W'],
                'dc_derate_factor': result['dc_derate_factor'],
                'fitted_Rs': fitted['Rs'],
                'fitted_Rsh': fitted['Rsh'],
                'fitted_n': fitted['n'],
                'timing_breakdown_ms': timings_ms,
            }
        )
    
    def _calculate_degradation_pct(self, device) -> float:
        """
        Calculate degradation percentage based on installation age
        
        Args:
            device: device_list instance
            
        Returns:
            Total degradation percentage
        """
        if not device.installation_date:
            return 0.0
        
        # Calculate age in years
        age_days = (date.today() - device.installation_date).days
        age_years = age_days / 365.25
        
        if age_years <= 0:
            return 0.0
        
        module = device.get_module_datasheet()
        if not module:
            return 0.0
        
        # Use measured degradation rate if available (most accurate)
        if device.measured_degradation_rate:
            total_degradation_pct = device.measured_degradation_rate * age_years
        else:
            # Use warranty-based estimation
            if age_years <= 1:
                total_degradation_pct = module.estimated_degradation_year1 or 0
            else:
                year1_deg = module.estimated_degradation_year1 or 0
                annual_deg = module.estimated_annual_degradation or 0
                total_degradation_pct = year1_deg + (age_years - 1) * annual_deg
        
        return max(0.0, total_degradation_pct)
    
    def validate_configuration(
        self,
        device: Any
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that device has required configuration for SDM Array
        
        Args:
            device: device_list instance
            
        Returns:
            (is_valid, error_message)
        """
        # Check if device has module datasheet
        module = device.get_module_datasheet()
        if not module:
            return False, "Device has no module datasheet configured"
        
        # Check if modules_in_series is set
        if not device.modules_in_series:
            return False, "modules_in_series not configured"
        
        # Check required module datasheet fields
        required_fields = {
            'pmax_stc': 'Maximum power at STC',
            'voc_stc': 'Open-circuit voltage at STC',
            'isc_stc': 'Short-circuit current at STC',
            'vmp_stc': 'MPP voltage at STC',
            'imp_stc': 'MPP current at STC',
            'temp_coeff_pmax': 'Temperature coefficient of Pmax',
            'temp_coeff_voc': 'Temperature coefficient of Voc',
            'temp_coeff_isc': 'Temperature coefficient of Isc',
        }
        
        for field, description in required_fields.items():
            value = getattr(module, field, None)
            if value is None or value == 0:
                return False, f"Module datasheet missing required field: {description} ({field})"
        
        return True, None
    
    def get_required_inputs(self) -> List[str]:
        """
        Get list of required input fields for SDM Array
        
        Returns:
            List of required field names
        """
        return [
            'device (with module_datasheet configured)',
            'irradiance (W/m²)',
            'ambient_temp or module_temp (°C)',
            'modules_in_series',
            'installation_date (for degradation)',
        ]
    
    def clear_cache(self, device_id: Optional[str] = None):
        """
        Clear parameter cache for a device or all devices
        
        Args:
            device_id: Device ID to clear cache for, or None to clear all
        """
        if device_id:
            if device_id in self._parameter_cache:
                del self._parameter_cache[device_id]
            # Also clear ModuleDS cache entries for this device
            keys_to_remove = [k for k in self._module_ds_cache.keys() if k.startswith(f"{device_id}_")]
            for k in keys_to_remove:
                del self._module_ds_cache[k]
            logger.info(f"Cleared cache for device {device_id}")
        else:
            self._parameter_cache.clear()
            self._module_ds_cache.clear()
            logger.info("Cleared all parameter caches")
    
    @staticmethod
    def get_historical_parameters(
        device_id: Optional[str] = None,
        module_datasheet_id: Optional[int] = None,
        model_code: str = 'sdm_array_v1',
        parameter_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve historical model parameters
        
        Useful for:
        - ML training to find optimal parameters
        - Using historical parameters for past date calculations
        
        Args:
            device_id: Device ID (for device-specific parameters)
            module_datasheet_id: Module datasheet ID (for datasheet-based parameters)
            model_code: Model code to filter by
            parameter_type: 'datasheet', 'device', or 'hybrid' (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            limit: Maximum number of records to return
            
        Returns:
            List of parameter dictionaries with metadata
        """
        if PowerModelParametersHistory is None:
            logger.warning("PowerModelParametersHistory model not available")
            return []
        
        try:
            queryset = PowerModelParametersHistory.objects.filter(
                model_code=model_code
            )
            
            if device_id:
                queryset = queryset.filter(device_id=device_id)
            if module_datasheet_id:
                queryset = queryset.filter(module_datasheet_id=module_datasheet_id)
            if parameter_type:
                queryset = queryset.filter(parameter_type=parameter_type)
            
            if start_date:
                queryset = queryset.filter(calculated_at__gte=start_date)
            if end_date:
                queryset = queryset.filter(calculated_at__lte=end_date)
            
            queryset = queryset.order_by('-calculated_at')
            
            if limit:
                queryset = queryset[:limit]
            
            results = []
            for record in queryset:
                results.append({
                    'id': record.id,
                    'device_id': record.device_id,
                    'module_datasheet_id': record.module_datasheet_id,
                    'asset_code': record.asset_code,
                    'model_code': record.model_code,
                    'model_version': record.model_version,
                    'parameter_type': record.parameter_type,
                    'parameters': record.parameters_dict,
                    'calculated_at': record.calculated_at,
                    'timezone': record.timezone,
                    'fit_quality': record.fit_quality,
                    'fit_method': record.fit_method,
                    'training_data_count': record.training_data_count,
                    'context_data': record.context_data or {},
                    'metadata': record.metadata or {},
                    'is_active': record.is_active,
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving historical parameters: {str(e)}")
            return []
    
    @staticmethod
    def get_latest_parameters(
        device_id: Optional[str] = None,
        module_datasheet_id: Optional[int] = None,
        model_code: str = 'sdm_array_v1',
        parameter_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent parameters
        
        Args:
            device_id: Device ID (for device-specific parameters)
            module_datasheet_id: Module datasheet ID (for datasheet-based parameters)
            model_code: Model code to filter by
            parameter_type: 'datasheet', 'device', or 'hybrid' (optional)
            
        Returns:
            Parameter dictionary or None if not found
        """
        if PowerModelParametersHistory is None:
            return None
        
        try:
            queryset = PowerModelParametersHistory.objects.filter(
                model_code=model_code,
                is_active=True
            )
            
            if device_id:
                queryset = queryset.filter(device_id=device_id)
            if module_datasheet_id:
                queryset = queryset.filter(module_datasheet_id=module_datasheet_id)
            if parameter_type:
                queryset = queryset.filter(parameter_type=parameter_type)
            
            record = queryset.order_by('-calculated_at').first()
            
            if record:
                return {
                    'parameters': record.parameters_dict,
                    'calculated_at': record.calculated_at,
                    'timezone': record.timezone,
                    'parameter_type': record.parameter_type,
                    'metadata': record.metadata or {},
                }
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving latest parameters: {str(e)}")
            return None
    
    @staticmethod
    def use_historical_parameters(
        device_id: Optional[str] = None,
        module_datasheet_id: Optional[int] = None,
        target_date: datetime = None,
        model_code: str = 'sdm_array_v1',
        parameter_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get parameters for a specific historical date
        
        Finds the most recent parameters calculated before or on the target date.
        Useful for calculating expected power for past dates using historical parameters.
        
        Args:
            device_id: Device ID (for device-specific parameters)
            module_datasheet_id: Module datasheet ID (for datasheet-based parameters)
            target_date: Target date for calculation
            model_code: Model code to filter by
            parameter_type: 'datasheet', 'device', or 'hybrid' (optional)
            
        Returns:
            Parameter dictionary or None if not found
        """
        if PowerModelParametersHistory is None:
            return None
        
        if target_date is None:
            target_date = django_timezone.now()
        
        try:
            queryset = PowerModelParametersHistory.objects.filter(
                model_code=model_code,
                calculated_at__lte=target_date
            )
            
            if device_id:
                queryset = queryset.filter(device_id=device_id)
            if module_datasheet_id:
                queryset = queryset.filter(module_datasheet_id=module_datasheet_id)
            if parameter_type:
                queryset = queryset.filter(parameter_type=parameter_type)
            
            record = queryset.order_by('-calculated_at').first()
            
            if record:
                return record.parameters_dict
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving historical parameters at {target_date}: {str(e)}")
            return None

