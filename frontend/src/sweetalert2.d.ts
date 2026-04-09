declare module 'sweetalert2' {
  export interface SweetAlertOptions {
    title?: string;
    text?: string;
    html?: string;
    icon?: 'success' | 'error' | 'warning' | 'info' | 'question';
    confirmButtonText?: string;
    width?: number | string;
    timer?: number;
    showConfirmButton?: boolean;
  }
  const Swal: {
    fire(options?: SweetAlertOptions): Promise<{ isConfirmed: boolean; isDismissed: boolean }>;
  };
  export default Swal;
}
