import Swal from 'sweetalert2';

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export async function showInvoiceBlockersDialog(blockers: Array<Record<string, unknown>>, title: string) {
  const lines = blockers.length
    ? blockers.map((b) => {
        const code = escapeHtml(String(b.code ?? ''));
        const msg = escapeHtml(String(b.message ?? ''));
        return `<p class="mb-3 text-start" style="margin:0 0 1rem 0"><strong>${code}</strong><br /><span style="font-weight:400">${msg}</span></p>`;
      })
    : ['<p class="text-start">No blocker details.</p>'];
  await Swal.fire({
    title,
    html: lines.join(''),
    icon: 'warning',
    confirmButtonText: 'OK',
    width: 560,
  });
}
