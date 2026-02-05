/**
 * Document overview page — shows PO metadata, line items, sections summary
 */
export default function DocumentOverview({ document, clauses, sections, lineItems, onStartReview, onBack }) {
  const clauseCount = clauses.length;
  const sectionCount = sections.length;
  const lineItemCount = lineItems.length;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Back link */}
      <button
        onClick={onBack}
        className="text-sm text-blue-600 hover:text-blue-800 mb-6 inline-block"
      >
        &larr; Back to documents
      </button>

      {/* Document metadata */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-2xl font-bold mb-4">{document.filename}</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 rounded">
            <div className="text-2xl font-bold text-gray-900">{document.total_lines || '-'}</div>
            <div className="text-sm text-gray-500">Lines</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded">
            <div className="text-2xl font-bold text-gray-900">{sectionCount}</div>
            <div className="text-sm text-gray-500">Sections</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded">
            <div className="text-2xl font-bold text-blue-600">{clauseCount}</div>
            <div className="text-sm text-gray-500">Clauses</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded">
            <div className="text-2xl font-bold text-gray-900">{lineItemCount}</div>
            <div className="text-sm text-gray-500">Line Items</div>
          </div>
        </div>
      </div>

      {/* Line items table */}
      {lineItems.length > 0 && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold">Line Items</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">#</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Part Number</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Description</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Quantity</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Quality Level</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {lineItems.map((item, index) => (
                  <tr key={item.id || index} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-500">{item.line_number || index + 1}</td>
                    <td className="px-4 py-3 text-sm font-mono">{item.part_number || '-'}</td>
                    <td className="px-4 py-3 text-sm">{item.description || '-'}</td>
                    <td className="px-4 py-3 text-sm">{item.quantity || '-'}</td>
                    <td className="px-4 py-3 text-sm">{item.quality_level || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sections summary */}
      {sections.length > 0 && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold">Sections</h3>
          </div>
          <div className="divide-y">
            {sections.map(section => {
              const sectionClauses = clauses.filter(c => c.section_id === section.id);
              return (
                <div key={section.id} className="px-6 py-3 flex justify-between items-center">
                  <div>
                    <span className="font-medium">{section.section_title || `Section ${section.order_index + 1}`}</span>
                    <span className="text-sm text-gray-500 ml-2">
                      Lines {section.start_line}–{section.end_line}
                    </span>
                  </div>
                  <span className="text-sm text-gray-500">
                    {sectionClauses.length} clause{sectionClauses.length !== 1 ? 's' : ''}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Start Review CTA */}
      <div className="text-center">
        <button
          onClick={onStartReview}
          className="px-8 py-3 bg-blue-600 text-white rounded-lg text-lg font-medium hover:bg-blue-700 shadow"
        >
          Start Review &mdash; {clauseCount} clause{clauseCount !== 1 ? 's' : ''}
        </button>
      </div>
    </div>
  );
}
