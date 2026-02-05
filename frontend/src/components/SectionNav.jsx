import ProgressBar from './ProgressBar';

/**
 * Sidebar navigation with sections, filters, and actions
 */
export default function SectionNav({
  sections,
  activeSectionId,
  onSectionChange,
  filter,
  onFilterChange,
  clauses,
  activeTab,
  onViewList,
  onExport,
  allAddressed,
}) {
  // Compute counts for the active tab
  const tabClauses = clauses.filter(c => {
    if (activeTab === 'po_wide') return c.scope_type === 'po_wide' || !c.scope_type;
    if (activeTab === 'line_specific') return c.scope_type === 'line_specific';
    return true;
  });

  const stats = {
    reviewed: tabClauses.filter(c => c.review_status === 'reviewed').length,
    flagged: tabClauses.filter(c => c.review_status === 'flagged').length,
    total: tabClauses.length,
  };

  // Sections to display — only those relevant to active tab
  const visibleSections = sections.filter(section => {
    return tabClauses.some(c => c.section_id === section.id);
  });

  const filterOptions = [
    { value: 'all', label: 'All' },
    { value: 'unreviewed', label: 'Unreviewed' },
    { value: 'flagged', label: 'Flagged' },
  ];

  return (
    <div className="bg-white rounded-lg shadow p-4 sticky top-4">
      <h3 className="font-semibold mb-4">Progress</h3>
      <ProgressBar
        reviewed={stats.reviewed}
        flagged={stats.flagged}
        total={stats.total}
      />

      {/* Section list */}
      {visibleSections.length > 0 && (
        <div className="mt-6">
          <h3 className="font-semibold mb-2">Sections</h3>
          <div className="flex flex-col gap-1 max-h-80 overflow-y-auto">
            <button
              onClick={() => onSectionChange(null)}
              className={`text-left px-3 py-2 rounded text-sm ${
                activeSectionId === null
                  ? 'bg-blue-100 text-blue-800'
                  : 'hover:bg-gray-100'
              }`}
            >
              All Sections ({tabClauses.length})
            </button>
            {visibleSections.map(section => {
              const count = tabClauses.filter(c => c.section_id === section.id).length;
              return (
                <button
                  key={section.id}
                  onClick={() => onSectionChange(section.id)}
                  className={`text-left px-3 py-2 rounded text-sm ${
                    activeSectionId === section.id
                      ? 'bg-blue-100 text-blue-800'
                      : 'hover:bg-gray-100'
                  }`}
                  title={section.section_title}
                >
                  {section.section_title} ({count})
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="mt-6">
        <h3 className="font-semibold mb-2">Filter</h3>
        <div className="flex flex-col gap-2">
          {filterOptions.map(option => {
            let count;
            if (option.value === 'all') count = tabClauses.length;
            else if (option.value === 'unreviewed') count = tabClauses.filter(c => c.review_status === 'unreviewed').length;
            else if (option.value === 'flagged') count = tabClauses.filter(c => c.review_status === 'flagged').length;

            return (
              <button
                key={option.value}
                onClick={() => onFilterChange(option.value)}
                className={`text-left px-3 py-2 rounded text-sm ${
                  filter === option.value
                    ? 'bg-blue-100 text-blue-800'
                    : 'hover:bg-gray-100'
                }`}
              >
                {option.label} ({count})
              </button>
            );
          })}
        </div>
      </div>

      {/* Actions */}
      <div className="mt-6 flex flex-col gap-2">
        <button
          onClick={onViewList}
          className="w-full px-3 py-2 text-sm border rounded hover:bg-gray-50"
        >
          View as List
        </button>
        <button
          onClick={() => onExport('json')}
          disabled={!allAddressed}
          className="w-full px-3 py-2 text-sm border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          title={!allAddressed ? 'Review or flag all clauses to export' : ''}
        >
          Export JSON
        </button>
        <button
          onClick={() => onExport('csv')}
          disabled={!allAddressed}
          className="w-full px-3 py-2 text-sm border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          title={!allAddressed ? 'Review or flag all clauses to export' : ''}
        >
          Export CSV
        </button>
      </div>
    </div>
  );
}
