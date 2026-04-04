import { useState } from 'react';

export function TokenEfficiencyPanel({ task, messages, context }) {
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [error, setError] = useState(null);

  const handleOptimize = async () => {
    if (!task || messages.length === 0) {
      setError('Please provide task and messages');
      return;
    }

    setIsOptimizing(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:5000/api/optimize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_text: task,
          incoming_messages: messages,
          prior_context: context || [],
          complexity: 0.6,
          urgency: 0.5,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const data = await response.json();
      if (data.success) {
        setOptimizationResult(data);
      } else {
        setError(data.error || 'Optimization failed');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setIsOptimizing(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 mt-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Token Efficiency Analysis</h2>

      <button
        onClick={handleOptimize}
        disabled={isOptimizing}
        className={`px-6 py-2 rounded-lg font-medium transition ${
          isOptimizing
            ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
            : 'bg-blue-600 text-white hover:bg-blue-700'
        }`}
      >
        {isOptimizing ? 'Optimizing...' : 'Analyze Token Efficiency'}
      </button>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {optimizationResult && (
        <div className="mt-6 space-y-4">
          {/* Token Comparison */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600 font-medium">Baseline Tokens</div>
              <div className="text-3xl font-bold text-gray-900 mt-2">
                {optimizationResult.baseline_tokens}
              </div>
              <div className="text-xs text-gray-500 mt-1">Full context</div>
            </div>

            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-sm text-blue-600 font-medium">Optimized Tokens</div>
              <div className="text-3xl font-bold text-blue-900 mt-2">
                {optimizationResult.optimized_tokens}
              </div>
              <div className="text-xs text-blue-600 mt-1">With efficiency pipeline</div>
            </div>

            <div className="bg-green-50 p-4 rounded-lg">
              <div className="text-sm text-green-600 font-medium">Savings</div>
              <div className="text-3xl font-bold text-green-900 mt-2">
                {optimizationResult.savings_pct.toFixed(1)}%
              </div>
              <div className="text-xs text-green-600 mt-1">
                {(optimizationResult.baseline_tokens - optimizationResult.optimized_tokens)} tokens saved
              </div>
            </div>
          </div>

          {/* Quality & Routing */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600 font-medium">Quality Proxy</div>
              <div className="text-2xl font-bold text-gray-900 mt-2">
                {optimizationResult.quality_proxy.toFixed(4)}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {optimizationResult.quality_proxy >= 0.98 ? '✓ Meets floor (0.98)' : '⚠ Below floor'}
              </div>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600 font-medium">Routed Model</div>
              <div className="text-lg font-bold text-gray-900 mt-2">
                {optimizationResult.routed_model}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Based on complexity/urgency
              </div>
            </div>
          </div>

          {/* Debug Details */}
          {optimizationResult.debug && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <details className="cursor-pointer">
                <summary className="font-medium text-gray-700 hover:text-gray-900">
                  Details & Breakdown
                </summary>
                <div className="mt-3 space-y-2 text-sm text-gray-600">
                  {optimizationResult.debug.compression_stats?.removed_redundant_sentences && (
                    <div>
                      • Compression: {optimizationResult.debug.compression_stats.removed_redundant_sentences} redundant sentences removed
                    </div>
                  )}
                  {optimizationResult.debug.sampling_stats?.sampled_count && (
                    <div>
                      • Semantic Sampling: {optimizationResult.debug.sampling_stats.sampled_count} / {optimizationResult.debug.sampling_stats.total_count} contexts retained
                    </div>
                  )}
                  <div>
                    • Cache Hit Rate: {(optimizationResult.debug.cache_hit_rate * 100).toFixed(1)}%
                  </div>
                  <div>
                    • Rehydration Events: {optimizationResult.debug.rehydration_events}
                  </div>
                </div>
              </details>
            </div>
          )}
        </div>
      )}

      {optimizationResult && (
        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700">
          <strong>How it works:</strong> The optimization pipeline compresses messages, samples important contexts using semantic scoring, prunes further, and routes to appropriate models. Quality is maintained via a 0.98 floor with fallback rehydration.
        </div>
      )}
    </div>
  );
}
