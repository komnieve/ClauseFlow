import { useState, useMemo } from 'react';
import SectionNav from './SectionNav';
import ClauseCard from './ClauseCard';
import ProgressBar from './ProgressBar';

/**
 * Tabbed review layout — PO-Wide / Line-Specific tabs, section nav, clause card
 * Falls back to flat list for V1 docs (no sections)
 */
export default function ReviewView({
  clauses,
  sections,
  lineItems,
  loading,
  onClauseUpdate,
  onViewList,
  onExport,
  onNavigateToLibrary,
}) {
  const hasV2 = sections.length > 0;
  const [activeTab, setActiveTab] = useState('po_wide');
  const [activeSectionId, setActiveSectionId] = useState(null);
  const [currentClauseIndex, setCurrentClauseIndex] = useState(0);
  const [filter, setFilter] = useState('all');

  // Compute filtered clauses through the chain: tab → section → status
  const filteredClauses = useMemo(() => {
    let result = clauses;

    if (hasV2) {
      // Filter by tab
      if (activeTab === 'po_wide') {
        result = result.filter(c => c.scope_type === 'po_wide' || !c.scope_type);
      } else if (activeTab === 'line_specific') {
        result = result.filter(c => c.scope_type === 'line_specific');
      }

      // Filter by section
      if (activeSectionId !== null) {
        result = result.filter(c => c.section_id === activeSectionId);
      }
    }

    // Filter by review status
    if (filter === 'unreviewed') {
      result = result.filter(c => c.review_status === 'unreviewed');
    } else if (filter === 'flagged') {
      result = result.filter(c => c.review_status === 'flagged');
    }

    return result;
  }, [clauses, activeTab, activeSectionId, filter, hasV2]);

  // Reset index when filters change
  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setActiveSectionId(null);
    setCurrentClauseIndex(0);
  };

  const handleSectionChange = (sectionId) => {
    setActiveSectionId(sectionId);
    setCurrentClauseIndex(0);
  };

  const handleFilterChange = (f) => {
    setFilter(f);
    setCurrentClauseIndex(0);
  };

  const currentClause = filteredClauses[currentClauseIndex];

  // Tab counts
  const poWideCount = clauses.filter(c => c.scope_type === 'po_wide' || !c.scope_type).length;
  const lineSpecificCount = clauses.filter(c => c.scope_type === 'line_specific').length;

  // Stats for all clauses (for export gating)
  const allAddressed = clauses.length > 0 && clauses.every(
    c => c.review_status === 'reviewed' || c.review_status === 'flagged'
  );

  // Section title for current clause
  const currentSectionTitle = currentClause?.section_id
    ? sections.find(s => s.id === currentClause.section_id)?.section_title
    : null;

  // V1 fallback: simple sidebar like the old view
  if (!hasV2) {
    const v1Stats = {
      reviewed: clauses.filter(c => c.review_status === 'reviewed').length,
      flagged: clauses.filter(c => c.review_status === 'flagged').length,
      total: clauses.length,
    };

    return (
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow p-4 sticky top-4">
            <h3 className="font-semibold mb-4">Progress</h3>
            <ProgressBar reviewed={v1Stats.reviewed} flagged={v1Stats.flagged} total={v1Stats.total} />

            <div className="mt-6">
              <h3 className="font-semibold mb-2">Filter</h3>
              <div className="flex flex-col gap-2">
                {[
                  { value: 'all', label: `All (${clauses.length})` },
                  { value: 'unreviewed', label: `Unreviewed (${clauses.filter(c => c.review_status === 'unreviewed').length})` },
                  { value: 'flagged', label: `Flagged (${clauses.filter(c => c.review_status === 'flagged').length})` },
                ].map(option => (
                  <button
                    key={option.value}
                    onClick={() => handleFilterChange(option.value)}
                    className={`text-left px-3 py-2 rounded text-sm ${
                      filter === option.value ? 'bg-blue-100 text-blue-800' : 'hover:bg-gray-100'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-6">
              <button onClick={onViewList} className="w-full px-3 py-2 text-sm border rounded hover:bg-gray-50">
                View as List
              </button>
            </div>
          </div>
        </div>

        <div className="lg:col-span-3">
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
            </div>
          ) : currentClause ? (
            <ClauseCard
              key={currentClause.id}
              clause={currentClause}
              onUpdate={onClauseUpdate}
              onNext={() => setCurrentClauseIndex(Math.min(currentClauseIndex + 1, filteredClauses.length - 1))}
              onPrev={() => setCurrentClauseIndex(Math.max(currentClauseIndex - 1, 0))}
              currentIndex={currentClauseIndex}
              totalCount={filteredClauses.length}
              onNavigateToLibrary={onNavigateToLibrary}
            />
          ) : (
            <div className="text-center py-12 text-gray-500">
              No clauses match the current filter.
            </div>
          )}
        </div>
      </div>
    );
  }

  // Unresolved reference count
  const unresolvedRefCount = clauses.reduce((acc, c) => {
    const links = c.reference_links || [];
    return acc + links.filter(l => l.match_status === 'unresolved').length;
  }, 0);

  // V2 tabbed view
  return (
    <div>
      {/* Tab bar + unresolved refs indicator */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex gap-1 bg-white rounded-lg shadow p-1 max-w-md">
        <button
          onClick={() => handleTabChange('po_wide')}
          className={`flex-1 px-4 py-2 rounded text-sm font-medium transition-colors ${
            activeTab === 'po_wide'
              ? 'bg-indigo-600 text-white'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          PO-Wide ({poWideCount})
        </button>
        <button
          onClick={() => handleTabChange('line_specific')}
          className={`flex-1 px-4 py-2 rounded text-sm font-medium transition-colors ${
            activeTab === 'line_specific'
              ? 'bg-teal-600 text-white'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          Line-Specific ({lineSpecificCount})
        </button>
        </div>
        {unresolvedRefCount > 0 && (
          <span className="flex items-center gap-1 text-sm text-red-600">
            <span className="w-2 h-2 bg-red-500 rounded-full inline-block"></span>
            {unresolvedRefCount} unresolved ref{unresolvedRefCount !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <SectionNav
            sections={sections}
            activeSectionId={activeSectionId}
            onSectionChange={handleSectionChange}
            filter={filter}
            onFilterChange={handleFilterChange}
            clauses={clauses}
            activeTab={activeTab}
            onViewList={onViewList}
            onExport={onExport}
            allAddressed={allAddressed}
          />
        </div>

        {/* Main content */}
        <div className="lg:col-span-3">
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
            </div>
          ) : currentClause ? (
            <ClauseCard
              key={currentClause.id}
              clause={currentClause}
              onUpdate={onClauseUpdate}
              onNext={() => setCurrentClauseIndex(Math.min(currentClauseIndex + 1, filteredClauses.length - 1))}
              onPrev={() => setCurrentClauseIndex(Math.max(currentClauseIndex - 1, 0))}
              currentIndex={currentClauseIndex}
              totalCount={filteredClauses.length}
              sectionTitle={currentSectionTitle}
              lineItems={lineItems}
              onNavigateToLibrary={onNavigateToLibrary}
            />
          ) : (
            <div className="text-center py-12 text-gray-500">
              No clauses match the current filter.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
