/**
 * ERP match status badge — shows matched/mismatched/new/external with color coding.
 */
export default function ERPStatusBadge({ status, revision, date, mismatchDetails, compact = false }) {
  const config = {
    matched: { label: 'Matched', className: 'bg-green-100 text-green-800 border-green-200', dot: 'bg-green-500' },
    mismatched: { label: 'Mismatch', className: 'bg-yellow-100 text-yellow-800 border-yellow-200', dot: 'bg-yellow-500' },
    not_found: { label: 'New', className: 'bg-red-100 text-red-800 border-red-200', dot: 'bg-red-500' },
    external_pending: { label: 'External', className: 'bg-gray-100 text-gray-700 border-gray-200', dot: 'bg-gray-400' },
  };

  const cfg = config[status] || config.not_found;

  if (compact) {
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${cfg.className}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`}></span>
        {cfg.label}
      </span>
    );
  }

  return (
    <div className={`inline-flex flex-col px-3 py-2 rounded-lg border ${cfg.className}`}>
      <div className="flex items-center gap-1.5">
        <span className={`w-2 h-2 rounded-full ${cfg.dot}`}></span>
        <span className="text-xs font-semibold">{cfg.label}</span>
      </div>
      {status === 'matched' && revision && (
        <span className="text-xs mt-0.5 opacity-75">ERP: {revision}{date ? ` (${date})` : ''}</span>
      )}
      {status === 'mismatched' && mismatchDetails && (
        <span className="text-xs mt-0.5">{mismatchDetails}</span>
      )}
      {status === 'not_found' && (
        <span className="text-xs mt-0.5 opacity-75">Not in ERP — needs to be added</span>
      )}
      {status === 'external_pending' && (
        <span className="text-xs mt-0.5 opacity-75">External document — manual verification</span>
      )}
    </div>
  );
}
