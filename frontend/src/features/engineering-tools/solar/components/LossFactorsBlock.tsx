import { useState, useEffect, type ChangeEvent } from 'react';
import { Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { Button } from '@/components/ui/button';

interface LossFactorsBlockProps {
  disabled?: boolean;
  onLossFactorsChange?: (params: {
    dcLossPct: number;
    acLossPct: number;
    shadowLossPct: number;
  }) => void;
  /** When true (e.g. in wizard), show content expanded and hide expand/collapse button */
  defaultExpanded?: boolean;
}

export default function LossFactorsBlock({ disabled, onLossFactorsChange, defaultExpanded }: LossFactorsBlockProps) {
  const [open, setOpen] = useState(!!defaultExpanded);
  const [dcLossPct, setDcLossPct] = useState<string>('1.5');
  const [acLossPct, setAcLossPct] = useState<string>('2.0');
  const [nearShadingLossPct, setNearShadingLossPct] = useState<string>('3.0');
  const [saving, setSaving] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);

  const handleSave = () => {
    setSaving(true);
    const dc = parseFloat(dcLossPct) || 0;
    const ac = parseFloat(acLossPct) || 0;
    const shadow = parseFloat(nearShadingLossPct) || 0;
    onLossFactorsChange?.({ dcLossPct: dc, acLossPct: ac, shadowLossPct: shadow });
    setTimeout(() => {
      setSaving(false);
      setIsEditMode(false);
    }, 200);
  };

  useEffect(() => {
    const dc = parseFloat(dcLossPct) || 0;
    const ac = parseFloat(acLossPct) || 0;
    const shadow = parseFloat(nearShadingLossPct) || 0;
    onLossFactorsChange?.({ dcLossPct: dc, acLossPct: ac, shadowLossPct: shadow });
  }, [dcLossPct, acLossPct, nearShadingLossPct, onLossFactorsChange]);

  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 p-2 pb-1">
        <CardTitle className="text-base">Loss Factors</CardTitle>
        {!defaultExpanded && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setOpen((prev) => !prev)}
            aria-label={open ? 'Collapse loss factors' : 'Expand loss factors'}
            className="text-lg leading-none px-2"
          >
            {open ? '˄' : '˅'}
          </Button>
        )}
      </CardHeader>
      {(open || defaultExpanded) && (
        <CardContent className="space-y-2 p-2 pt-0">
          <TooltipProvider>
            <div className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-3">
              <div className="space-y-1">
                <div className="flex items-center gap-1">
                  <Label htmlFor="dc-loss">DC Loss in %</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="w-3 h-3 text-muted-foreground cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      DC Loss for string inverters: ~1.2%. For central inverters: ~1.5%.
                    </TooltipContent>
                  </Tooltip>
                </div>
                <Input
                  id="dc-loss"
                  type="number"
                  min={0}
                  step={0.1}
                  value={dcLossPct}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setDcLossPct(e.target.value)}
                  placeholder="e.g. 1.5"
                  disabled={disabled || !isEditMode}
                  readOnly={!isEditMode}
                  className={!isEditMode ? 'h-8 text-sm bg-muted' : 'h-8 text-sm'}
                />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-1">
                  <Label htmlFor="ac-loss">AC Loss in %</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="w-3 h-3 text-muted-foreground cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>Typical AC loss overall ≈ 2%.</TooltipContent>
                  </Tooltip>
                </div>
                <Input
                  id="ac-loss"
                  type="number"
                  min={0}
                  step={0.1}
                  value={acLossPct}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setAcLossPct(e.target.value)}
                  placeholder="e.g. 2.0"
                  disabled={disabled || !isEditMode}
                  readOnly={!isEditMode}
                  className={!isEditMode ? 'h-8 text-sm bg-muted' : 'h-8 text-sm'}
                />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-1">
                  <Label htmlFor="near-shading-loss">Near shading loss in %</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="w-3 h-3 text-muted-foreground cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      No obstacles: ~0%. Trees at perimeter: 2–5%. Trees around site: 5–8%.
                    </TooltipContent>
                  </Tooltip>
                </div>
                <Input
                  id="near-shading-loss"
                  type="number"
                  min={0}
                  step={0.1}
                  value={nearShadingLossPct}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setNearShadingLossPct(e.target.value)}
                  placeholder="e.g. 3.0"
                  disabled={disabled || !isEditMode}
                  readOnly={!isEditMode}
                  className={!isEditMode ? 'h-8 text-sm bg-muted' : 'h-8 text-sm'}
                />
              </div>
            </div>
          </TooltipProvider>
          <div className="flex flex-wrap items-center gap-2 mt-1">
            {isEditMode ? (
              <Button onClick={handleSave} disabled={saving || disabled} className="text-white">
                {saving ? 'Saving…' : 'Save Loss Factors'}
              </Button>
            ) : (
              <>
                <Button type="button" disabled className="bg-green-600 hover:bg-green-600 text-white">
                  Saved
                </Button>
                <Button type="button" variant="outline" onClick={() => setIsEditMode(true)}>
                  Edit
                </Button>
              </>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
