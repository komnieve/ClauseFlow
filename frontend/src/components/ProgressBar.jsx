/**
 * Progress bar showing review status
 */
export default function ProgressBar({ reviewed, flagged, total }) {
  const reviewedPercent = total > 0 ? (reviewed / total) * 100 : 0;
  const flaggedPercent = total > 0 ? (flagged / total) * 100 : 0;
  const unreviewed = total - reviewed - flagged;

  return (
    <div className="w-full">
      <div className="flex justify-between text-sm text-gray-600 mb-1">
        <span>{reviewed} reviewed</span>
        <span>{flagged} flagged</span>
        <span>{unreviewed} remaining</span>
      </div>
      <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden flex">
        <div
          className="h-full bg-green-500 transition-all duration-300"
          style={{ width: `${reviewedPercent}%` }}
        />
        <div
          className="h-full bg-yellow-500 transition-all duration-300"
          style={{ width: `${flaggedPercent}%` }}
        />
      </div>
      <div className="text-center text-sm text-gray-500 mt-1">
        {Math.round(reviewedPercent)}% complete
      </div>
    </div>
  );
}
