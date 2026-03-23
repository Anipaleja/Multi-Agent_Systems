import { useState } from 'react';

const PREDEFINED_TASKS = [
  { id: 1, label: "Write a product spec for a note-taking app", value: "Write a product spec for a note-taking app" },
  { id: 2, label: "Design a REST API for a bookstore", value: "Design a REST API for a bookstore" },
  { id: 3, label: "Create a marketing plan for a new coffee brand", value: "Create a marketing plan for a new coffee brand" },
  { id: 4, label: "Outline a curriculum for teaching Python to beginners", value: "Outline a curriculum for teaching Python to beginners" },
];

const PROVIDERS = [
  {
    id: 'deepseek',
    name: 'DeepSeek',
    endpoint: 'https://api.deepseek.com/v1/chat/completions',
    model: 'deepseek-chat',
    apiKeyPlaceholder: 'sk-...'
  },
  {
    id: 'groq',
    name: 'Groq',
    endpoint: 'https://api.groq.com/openai/v1/chat/completions',
    model: 'llama-3.3-70b-versatile',
    apiKeyPlaceholder: 'gsk_...'
  },
  {
    id: 'openai',
    name: 'OpenAI',
    endpoint: 'https://api.openai.com/v1/chat/completions',
    model: 'gpt-4o-mini',
    apiKeyPlaceholder: 'sk-proj-...'
  }
];

const AGENT_CONFIGS = [
  {
    id: 1,
    name: "Architect",
    role: "Plans and structures",
    provider: 'deepseek',
    color: "blue",
    prompt: (task) => `Task: ${task}\n\nYou are the Architect agent. Break this task into a clear structural plan with 3-4 components. Be concise.`
  },
  {
    id: 2,
    name: "Builder",
    role: "Executes the plan",
    provider: 'groq',
    color: "green",
    prompt: (task, agent1Output) => `Task: ${task}\n\n[ARCHITECT PLAN]\n${agent1Output}\n[/ARCHITECT PLAN]\n\nYou are the Builder agent. Execute the plan above. Build out the core content.`
  },
  {
    id: 3,
    name: "Reviewer",
    role: "QA and synthesis",
    provider: 'openai',
    color: "purple",
    prompt: (task, agent1Output, agent2Output) => `Task: ${task}\n\n[ARCHITECT PLAN]\n${agent1Output}\n[/ARCHITECT PLAN]\n\n[BUILDER OUTPUT]\n${agent2Output}\n[/BUILDER OUTPUT]\n\nYou are the Reviewer agent. Review both outputs, fill gaps, and write the final polished result.`
  }
];

function App() {
  const [selectedTask, setSelectedTask] = useState(PREDEFINED_TASKS[0].value);
  const [isRunning, setIsRunning] = useState(false);
  const [apiKeys, setApiKeys] = useState({
    deepseek: import.meta.env.VITE_DEEPSEEK_API_KEY || '',
    groq: import.meta.env.VITE_GROQ_API_KEY || '',
    openai: import.meta.env.VITE_OPENAI_API_KEY || ''
  });
  const [agents, setAgents] = useState([
    { id: 1, status: 'idle', output: '', usage: null },
    { id: 2, status: 'idle', output: '', usage: null },
    { id: 3, status: 'idle', output: '', usage: null }
  ]);
  const [tokenStats, setTokenStats] = useState(null);

  const callAI = async (promptText, agentName, providerId) => {
    const provider = PROVIDERS.find(p => p.id === providerId);
    const apiKey = apiKeys[providerId];

    if (!apiKey) {
      throw new Error(`API key not set for ${provider.name}`);
    }

    const response = await fetch(provider.endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: provider.model,
        max_tokens: 600,
        messages: [
          { role: 'user', content: promptText }
        ]
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage;
      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.error?.message || errorJson.message || errorText;
      } catch {
        errorMessage = errorText;
      }
      throw new Error(`API Error for ${agentName} (${provider.name}): ${errorMessage}`);
    }

    const data = await response.json();

    // Extract token usage and content from response
    // OpenAI-compatible format (DeepSeek, Groq, OpenAI all use this)
    const content = data.choices[0].message.content;
    const usage = {
      input_tokens: data.usage.prompt_tokens,
      output_tokens: data.usage.completion_tokens,
      total_tokens: data.usage.total_tokens
    };

    return { content, usage };
  };

  const updateAgentStatus = (agentId, status, output = null, usage = null) => {
    setAgents(prev => prev.map(agent =>
      agent.id === agentId
        ? { ...agent, status, output: output !== null ? output : agent.output, usage: usage !== null ? usage : agent.usage }
        : agent
    ));
  };

  const calculateTokenStats = (agentResults) => {
    const agent1 = agentResults[0];
    const agent2 = agentResults[1];
    const agent3 = agentResults[2];

    // Calculate redundant tokens
    const agent2RedundantTokens = agent1.usage.output_tokens;
    const agent3RedundantTokens = agent1.usage.output_tokens + agent2.usage.output_tokens;

    const totalRedundantTokens = agent2RedundantTokens + agent3RedundantTokens;

    const totalTokens =
      agent1.usage.input_tokens + agent1.usage.output_tokens +
      agent2.usage.input_tokens + agent2.usage.output_tokens +
      agent3.usage.input_tokens + agent3.usage.output_tokens;

    const uniqueTokens = totalTokens - totalRedundantTokens;
    const efficiencyScore = Math.round((uniqueTokens / totalTokens) * 100);

    const totalPromptTokens = agent1.usage.input_tokens + agent2.usage.input_tokens + agent3.usage.input_tokens;
    const totalCompletionTokens = agent1.usage.output_tokens + agent2.usage.output_tokens + agent3.usage.output_tokens;

    return {
      totalTokens,
      uniqueTokens,
      redundantTokens: totalRedundantTokens,
      efficiencyScore,
      totalPromptTokens,
      totalCompletionTokens,
      agent2RedundantTokens,
      agent3RedundantTokens
    };
  };

  const runAgents = async () => {
    // Check all API keys are present
    const missingKeys = AGENT_CONFIGS.filter(config => !apiKeys[config.provider]);
    if (missingKeys.length > 0) {
      const missingProviders = missingKeys.map(config =>
        PROVIDERS.find(p => p.id === config.provider).name
      ).join(', ');
      alert(`Please enter API keys for: ${missingProviders}`);
      return;
    }

    setIsRunning(true);
    setTokenStats(null);

    // Reset all agents
    setAgents([
      { id: 1, status: 'idle', output: '', usage: null },
      { id: 2, status: 'idle', output: '', usage: null },
      { id: 3, status: 'idle', output: '', usage: null }
    ]);

    try {
      // Agent 1: Architect (DeepSeek)
      updateAgentStatus(1, 'running');
      const agent1Response = await callAI(
        AGENT_CONFIGS[0].prompt(selectedTask),
        'Architect',
        AGENT_CONFIGS[0].provider
      );
      const agent1Output = agent1Response.content;
      const agent1Usage = agent1Response.usage;
      updateAgentStatus(1, 'done', agent1Output, agent1Usage);

      // Agent 2: Builder (Groq)
      updateAgentStatus(2, 'running');
      const agent2Response = await callAI(
        AGENT_CONFIGS[1].prompt(selectedTask, agent1Output),
        'Builder',
        AGENT_CONFIGS[1].provider
      );
      const agent2Output = agent2Response.content;
      const agent2Usage = agent2Response.usage;
      updateAgentStatus(2, 'done', agent2Output, agent2Usage);

      // Agent 3: Reviewer (OpenAI)
      updateAgentStatus(3, 'running');
      const agent3Response = await callAI(
        AGENT_CONFIGS[2].prompt(selectedTask, agent1Output, agent2Output),
        'Reviewer',
        AGENT_CONFIGS[2].provider
      );
      const agent3Output = agent3Response.content;
      const agent3Usage = agent3Response.usage;
      updateAgentStatus(3, 'done', agent3Output, agent3Usage);

      // Calculate token statistics
      const stats = calculateTokenStats([
        { usage: agent1Usage },
        { usage: agent2Usage },
        { usage: agent3Usage }
      ]);
      setTokenStats(stats);

    } catch (error) {
      console.error('Error running agents:', error);
      alert(`Error: ${error.message}`);
      // Mark currently running agent as error
      setAgents(prev => prev.map(agent =>
        agent.status === 'running' ? { ...agent, status: 'error' } : agent
      ));
    } finally {
      setIsRunning(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'idle': return 'bg-gray-200 text-gray-600';
      case 'running': return 'bg-amber-200 text-amber-800 animate-pulse';
      case 'done': return 'bg-green-200 text-green-800';
      case 'error': return 'bg-red-200 text-red-800';
      default: return 'bg-gray-200 text-gray-600';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'idle': return 'Waiting...';
      case 'running': return 'Thinking...';
      case 'done': return 'Complete';
      case 'error': return 'Failed';
      default: return 'Waiting...';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-3xl font-bold text-gray-900">Multi-Agent Test Environment</h1>
            <span className="text-sm bg-blue-100 text-blue-800 px-3 py-1 rounded-full">Nexus Demo</span>
          </div>

          {/* API Key Inputs for all providers */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              API Keys (Each agent uses a different provider)
            </label>
            <div className="space-y-3">
              {PROVIDERS.map((provider, index) => {
                const agentConfig = AGENT_CONFIGS.find(a => a.provider === provider.id);
                return (
                  <div key={provider.id} className="flex items-center space-x-3">
                    <div className="flex-shrink-0 w-32">
                      <span className="text-sm font-medium text-gray-700">
                        {provider.name}
                      </span>
                      <br />
                      <span className="text-xs text-gray-500">
                        (Agent {agentConfig?.id}: {agentConfig?.name})
                      </span>
                    </div>
                    <input
                      type="password"
                      value={apiKeys[provider.id]}
                      onChange={(e) => setApiKeys(prev => ({ ...prev, [provider.id]: e.target.value }))}
                      placeholder={provider.apiKeyPlaceholder}
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    />
                  </div>
                );
              })}
            </div>
          </div>

          {/* Task Selection */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select a task for agents to complete:
            </label>
            <select
              value={selectedTask}
              onChange={(e) => setSelectedTask(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isRunning}
            >
              {PREDEFINED_TASKS.map(task => (
                <option key={task.id} value={task.value}>
                  {task.label}
                </option>
              ))}
            </select>
          </div>

          {/* Run Button */}
          <button
            onClick={runAgents}
            disabled={isRunning || !apiKeys.deepseek || !apiKeys.groq || !apiKeys.openai}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-3 px-6 rounded-lg transition-colors flex items-center justify-center"
          >
            <span className="mr-2">▶</span>
            {isRunning ? 'Running Agents...' : 'Run Agents'}
          </button>

          {/* Info */}
          <div className="mt-3 text-xs text-gray-500 text-center">
            Each agent uses a different AI provider to complete the task sequentially
          </div>
        </div>

        {/* Agent Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {agents.map((agent, index) => {
            const config = AGENT_CONFIGS[index];
            const provider = PROVIDERS.find(p => p.id === config.provider);
            return (
              <div key={agent.id} className="bg-white rounded-lg shadow-sm p-6">
                <div className="mb-4">
                  <h3 className="text-xl font-bold text-gray-900">Agent {agent.id}</h3>
                  <p className="text-sm text-gray-600 font-medium">{config.name}</p>
                  <p className="text-xs text-gray-500">{config.role}</p>
                  <div className="mt-2">
                    <span className="inline-block px-2 py-1 bg-indigo-100 text-indigo-800 text-xs font-semibold rounded">
                      {provider.name} ({provider.model})
                    </span>
                  </div>
                </div>

              {/* Status */}
              <div className={`inline-block px-3 py-1 rounded-full text-sm font-medium mb-4 ${getStatusColor(agent.status)}`}>
                {getStatusText(agent.status)}
              </div>

              {/* Output */}
              <div className="mb-4 bg-gray-50 rounded p-3 min-h-32 max-h-64 overflow-y-auto">
                <p className="text-xs text-gray-700 whitespace-pre-wrap break-words">
                  {agent.output || 'No output yet...'}
                </p>
              </div>

              {/* Token Usage */}
              {agent.usage && (
                <div className="border-t pt-4">
                  <p className="text-xs font-semibold text-gray-700 mb-2">Token Usage</p>
                  <div className="space-y-1 text-xs text-gray-600">
                    <div className="flex justify-between">
                      <span>In:</span>
                      <span className="font-mono">{agent.usage.input_tokens.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Out:</span>
                      <span className="font-mono">{agent.usage.output_tokens.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between border-t pt-1">
                      <span className="font-semibold">Total:</span>
                      <span className="font-mono font-semibold">{agent.usage.total_tokens.toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
            );
          })}
        </div>

        {/* Token Usage Dashboard */}
        {tokenStats && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">TOKEN USAGE DASHBOARD</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div>
                <p className="text-sm text-gray-600 mb-1">Total tokens used</p>
                <p className="text-3xl font-bold text-gray-900">{tokenStats.totalTokens.toLocaleString()}</p>
              </div>

              <div>
                <p className="text-sm text-gray-600 mb-1">Efficiency score</p>
                <div className="flex items-center">
                  <p className="text-3xl font-bold text-gray-900 mr-4">{tokenStats.efficiencyScore}%</p>
                  <div className="flex-1 bg-gray-200 rounded-full h-4">
                    <div
                      className={`h-4 rounded-full ${tokenStats.efficiencyScore > 50 ? 'bg-green-500' : 'bg-red-500'}`}
                      style={{ width: `${tokenStats.efficiencyScore}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="bg-green-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Unique / new tokens</p>
                <p className="text-2xl font-bold text-green-700">
                  {tokenStats.uniqueTokens.toLocaleString()}
                  <span className="text-lg ml-2">({Math.round((tokenStats.uniqueTokens / tokenStats.totalTokens) * 100)}%)</span>
                </p>
              </div>

              <div className="bg-red-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Redundant context tokens</p>
                <p className="text-2xl font-bold text-red-700">
                  {tokenStats.redundantTokens.toLocaleString()}
                  <span className="text-lg ml-2">({Math.round((tokenStats.redundantTokens / tokenStats.totalTokens) * 100)}%)</span>
                </p>
              </div>
            </div>

            {/* Breakdown Bar Chart */}
            <div className="mb-4">
              <p className="text-sm font-semibold text-gray-700 mb-3">Token Breakdown by Agent</p>
              {agents.map((agent, index) => (
                agent.usage && (
                  <div key={agent.id} className="mb-3">
                    <div className="flex items-center mb-1">
                      <span className="text-xs font-medium text-gray-700 w-24">Agent {agent.id}</span>
                      <div className="flex-1 bg-gray-200 rounded-full h-6 flex overflow-hidden">
                        <div
                          className="bg-blue-500 flex items-center justify-center text-white text-xs font-semibold"
                          style={{ width: `${(agent.usage.input_tokens / tokenStats.totalTokens) * 100}%` }}
                          title={`Prompt: ${agent.usage.input_tokens}`}
                        >
                          {agent.usage.input_tokens > 30 && agent.usage.input_tokens}
                        </div>
                        <div
                          className="bg-green-500 flex items-center justify-center text-white text-xs font-semibold"
                          style={{ width: `${(agent.usage.output_tokens / tokenStats.totalTokens) * 100}%` }}
                          title={`Completion: ${agent.usage.output_tokens}`}
                        >
                          {agent.usage.output_tokens > 30 && agent.usage.output_tokens}
                        </div>
                      </div>
                      <span className="text-xs text-gray-600 ml-3 w-16 text-right">{agent.usage.total_tokens}</span>
                    </div>
                  </div>
                )
              ))}
            </div>

            <div className="flex items-center text-xs text-gray-600 mt-4">
              <div className="flex items-center mr-6">
                <div className="w-4 h-4 bg-blue-500 rounded mr-2"></div>
                <span>Prompt tokens</span>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 bg-green-500 rounded mr-2"></div>
                <span>Completion tokens</span>
              </div>
            </div>

            {/* Explanation */}
            <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm text-gray-700">
                <span className="font-semibold">What this demonstrates:</span> In this sequential agent chain,
                Agent 2 re-ingests Agent 1's full output ({agents[0]?.usage?.output_tokens || 0} tokens),
                and Agent 3 re-ingests both previous outputs ({(agents[0]?.usage?.output_tokens || 0) + (agents[1]?.usage?.output_tokens || 0)} tokens).
                This redundancy represents <span className="font-bold">{tokenStats.redundantTokens.toLocaleString()} wasted tokens</span> that
                Nexus middleware would eliminate by maintaining a shared context store.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
