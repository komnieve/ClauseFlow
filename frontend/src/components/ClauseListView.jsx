/**
 * Full-width table view of all clauses with Section and Scope columns
 */
export default function ClauseListView({ clauses, sections, onSelectClause, onBackToReview }) {
  const sectionMap = {};
  for (const s of sections) {
    sectionMap[s.id] = s.section_title;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">All Clauses</h2>
        <button
          onClick={onBackToReview}
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
        >
          Back to Review
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Lines</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Clause</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Section</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Scope</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Type</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {clauses.map((clause, index) => (
              <tr
                key={clause.id}
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => onSelectClause(clause, index)}
              >
                <td className="px-4 py-3 text-sm text-gray-500">
                  {clause.start_line}-{clause.end_line}
                </td>
                <td className="px-4 py-3 text-sm">
                  {clause.clause_number || '-'}
                  {clause.clause_title && ` - ${clause.clause_title}`}
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">
                  {clause.section_id ? (sectionMap[clause.section_id] || '-') : '-'}
                </td>
                <td className="px-4 py-3 text-sm">
                  {clause.scope_type === 'po_wide' && (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-800">PO-Wide</span>
                  )}
                  {clause.scope_type === 'line_specific' && (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-teal-100 text-teal-800">Line-Specific</span>
                  )}
                  {!clause.scope_type && '-'}
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">{clause.chunk_type}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs ${
                    clause.review_status === 'reviewed' ? 'bg-green-100 text-green-800' :
                    clause.review_status === 'flagged' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {clause.review_status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
