import React, { useState, useEffect, useRef } from 'react';
import {
  ArrowRight,
  Play,
  CheckCircle,
  LogOut,
  Download,
  Settings,
  Bug,
  Activity,
  Eye,
  EyeOff,
  Monitor,
  Zap,
  X,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  GitBranch
} from 'lucide-react';

import StepProgressDisplay from './StepProgressDisplay';
import LLMIODisplay from './LLMIODisplay';
import StepVisualization from './StepVisualization';
import DebugPanel from './DebugPanel';
import { useStepProgress } from '../hooks/useStepProgress';
import { useLLMInteractions } from '../hooks/useLLMInteractions';
import { useSessionWebSocket } from '../hooks/useWebSocket';
import { sessionApi, Session, Message } from '../api/sessionApi';
import { handleError } from '../utils/errorHandler';

interface EnhancedSessionTheaterProps {
  sessionId: number;
  onExit: () => void;
  theme?: any;
  enableDebugPanel?: boolean;
  enableStepProgress?: boolean;
  enableLLMDebug?: boolean;
  autoRefresh?: boolean;
  compactMode?: boolean;
}

const EnhancedSessionTheater: React.FC<EnhancedSessionTheaterProps> = ({
  sessionId,
  onExit,
  theme,
  enableDebugPanel = true,
  enableStepProgress = true,
  enableLLMDebug = true,
  autoRefresh = true,
  compactMode = false
}) => {
  // 基础状态
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [generating, setGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState<'theater' | 'progress' | 'llm' | 'visualization'>('theater');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 调试面板状态
  const [debugPanelVisible, setDebugPanelVisible] = useState(false);
  const [debugPanelSize, setDebugPanelSize] = useState<'small' | 'medium' | 'large'>('medium');

  // 面板展开状态
  const [leftPanelExpanded, setLeftPanelExpanded] = useState(true);
  const [rightPanelExpanded, setRightPanelExpanded] = useState(true);

  // 使用自定义hooks
  const {
    flowData,
    progressData,
    loading: progressLoading,
    error: progressError,
    refetch: refetchProgress
  } = useStepProgress({
    sessionId,
    autoRefresh,
    includeDetails: true
  });

  const {
    interactions,
    statistics: llmStats,
    loading: llmLoading,
    error: llmError,
    refetch: refetchLLM
  } = useLLMInteractions({
    sessionId,
    autoRefresh,
    includeDetails: true
  });

  const {
    connected: wsConnected,
    lastMessage,
    reconnect: wsReconnect
  } = useSessionWebSocket(sessionId, {
    autoConnect: true,
    enableLogging: true
  });

  // 加载基础数据
  const loadData = async () => {
    try {
      // 加载会话详情
      const sessionData = await sessionApi.getSession(sessionId);
      setSession(sessionData);

      // 加载会话消息
      const messagesData = await sessionApi.getMessages(sessionId, { page_size: 100 });
      setMessages(messagesData.items);
    } catch (error) {
      handleError(error);
    }
  };

  useEffect(() => {
    loadData();
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, generating]);

  // 处理WebSocket消息
  useEffect(() => {
    if (lastMessage) {
      switch (lastMessage.event) {
        case 'message_created':
          // 新消息创建
          if (lastMessage.data?.message) {
            setMessages(prev => [...prev, lastMessage.data.message]);
          }
          break;
        case 'session_status_changed':
          // 会话状态变化
          if (lastMessage.data?.new_status && session) {
            setSession(prev => prev ? {
              ...prev,
              status: lastMessage.data.new_status,
              updated_at: new Date().toISOString()
            } : null);
          }
          break;
        case 'step_completed':
        case 'llm_response_completed':
          // 重新加载进度和LLM数据
          refetchProgress();
          refetchLLM();
          break;
      }
    }
  }, [lastMessage, session, refetchProgress, refetchLLM]);

  // 执行下一步
  const handleNextStep = async () => {
    if (!session) return;
    setGenerating(true);
    try {
      const result = await sessionApi.executeNextStep(session.id);

      if (result.message) {
        setMessages(prev => [...prev, result.message]);
      }

      if (result.execution_info?.is_finished) {
        setSession(prev => prev ? {
          ...prev,
          status: 'finished',
          updated_at: new Date().toISOString()
        } : null);
      }

      // 刷新进度数据
      refetchProgress();
      refetchLLM();
    } catch (error) {
      handleError(error);
    } finally {
      setGenerating(false);
    }
  };

  // 结束会话
  const handleFinish = async () => {
    if (!session) return;

    if (confirm("确定要结束当前会话吗？")) {
      try {
        await sessionApi.terminateSession(session.id);
        setSession(prev => prev ? {
          ...prev,
          status: 'finished',
          updated_at: new Date().toISOString()
        } : null);
      } catch (error) {
        handleError(error);
      }
    }
  };

  // 导出会话数据
  const handleExport = async () => {
    try {
      const exportData = {
        session,
        messages,
        progressData,
        llmStats,
        interactions,
        exportTime: new Date().toISOString()
      };

      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `session_${sessionId}_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      handleError(error);
    }
  };

  if (!session) return <div className="p-10 text-center">Loading Enhanced Theater...</div>;

  const isFinished = session.status === 'finished' || session.status === 'terminated';

  return (
    <div className="h-screen flex flex-col bg-gray-100 relative">
      {/* 主头部 */}
      <div className="bg-white border-b px-4 py-3 flex justify-between items-center shrink-0 z-20">
        <div className="flex items-center gap-4">
          <button onClick={onExit} className="p-2 hover:bg-gray-100 rounded-full">
            <ArrowRight className="rotate-180" />
          </button>
          <div>
            <h2 className="font-bold text-gray-900 flex items-center gap-2">
              {session.topic}
              <span className={`px-2 py-1 text-xs rounded-full ${
                isFinished ? 'bg-gray-100 text-gray-600' : 'bg-green-100 text-green-600'
              }`}>
                {isFinished ? '已结束' : '进行中'}
              </span>
              {wsConnected && (
                <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-600 flex items-center">
                  <Zap className="w-3 h-3 mr-1" />
                  Live
                </span>
              )}
            </h2>
            <div className="text-xs text-gray-500 mt-0.5 flex gap-2">
              <span>Template: {session.flow_template_id}</span>
              <span>•</span>
              <span>Round: {session.current_round + 1}</span>
              {progressData && (
                <>
                  <span>•</span>
                  <span>Progress: {progressData.summary.progress_percentage.toFixed(1)}%</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* 功能标签页 */}
          <div className="flex items-center bg-gray-100 rounded-lg p-1">
            {[
              { id: 'theater', label: '剧场', icon: <MessageSquare className="w-4 h-4" /> },
              { enableStepProgress && { id: 'progress', label: '进度', icon: <Activity className="w-4 h-4" /> },
              { enableLLMDebug && { id: 'llm', label: 'LLM', icon: <Zap className="w-4 h-4" /> },
              { enableStepProgress && { id: 'visualization', label: '可视化', icon: <Monitor className="w-4 h-4" /> }
            ].filter(Boolean).map((tab: any) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {tab.icon}
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </div>

          {/* 操作按钮 */}
          <button onClick={handleExport} className="p-2 hover:bg-gray-100 rounded-full" title="导出数据">
            <Download />
          </button>

          {enableDebugPanel && (
            <button
              onClick={() => setDebugPanelVisible(!debugPanelVisible)}
              className={`p-2 rounded-full transition-colors ${
                debugPanelVisible ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100'
              }`}
              title="调试面板"
            >
              <Bug />
            </button>
          )}

          <button
            onClick={() => wsReconnect()}
            className={`p-2 rounded-full transition-colors ${
              wsConnected ? 'text-green-600' : 'text-red-600 hover:bg-red-100'
            }`}
            title="重新连接"
          >
            <Settings />
          </button>
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧面板 - 步骤进度 */}
        {enableStepProgress && leftPanelExpanded && (
          <div className="w-80 border-r bg-white flex flex-col">
            <div className="flex items-center justify-between p-3 border-b">
              <h3 className="font-medium text-gray-900">步骤进度</h3>
              <button
                onClick={() => setLeftPanelExpanded(false)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <ChevronDown className="w-4 h-4 rotate-270" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <StepProgressDisplay
                sessionId={sessionId}
                compact={true}
                showDetails={false}
                autoRefresh={autoRefresh}
              />
            </div>
          </div>
        )}

        {/* 左侧面板收起按钮 */}
        {enableStepProgress && !leftPanelExpanded && (
          <div className="w-8 border-r bg-white flex items-center justify-center">
            <button
              onClick={() => setLeftPanelExpanded(true)}
              className="p-1 hover:bg-gray-100 rounded"
            >
              <ChevronUp className="w-4 h-4 rotate-90" />
            </button>
          </div>
        )}

        {/* 中央内容区域 */}
        <div className="flex-1 flex flex-col">
          {activeTab === 'theater' && (
            <>
              {/* 消息区域 */}
              <div className="flex-1 overflow-y-auto p-6">
                {messages.length === 0 ? (
                  <div className="text-center text-gray-400 py-20">
                    <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>舞台已就绪，等待开场...</p>
                  </div>
                ) : (
                  <div className="space-y-6 max-w-4xl mx-auto">
                    {messages.map(msg => {
                      const isTeacher = msg.speaker_role_name?.includes('老师') || false;
                      const roleColor = isTeacher && theme ? `${theme.bgSoft} ${theme.text}` : 'bg-gray-100 text-gray-900';

                      return (
                        <div key={msg.id} className="flex gap-4 max-w-3xl">
                          <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center shrink-0 font-bold text-gray-600 text-sm">
                            {msg.speaker_role_name?.[0] || '?'}
                          </div>
                          <div className="space-y-1 flex-1">
                            <div className="flex items-baseline gap-2">
                              <span className="font-bold text-sm text-gray-900">
                                {msg.speaker_role_name || '未知角色'}
                              </span>
                              <span className="text-xs text-gray-400">
                                {new Date(msg.created_at).toLocaleTimeString()}
                              </span>
                              {msg.target_role_name && (
                                <span className="text-xs text-gray-400">to {msg.target_role_name}</span>
                              )}
                            </div>
                            <div className={`px-4 py-3 rounded-2xl rounded-tl-none ${roleColor} text-sm leading-relaxed shadow-sm`}>
                              {msg.content}
                            </div>
                            <div className="flex gap-2 opacity-0 hover:opacity-100 transition-opacity">
                              <button className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                                <GitBranch size={10} />
                                创建分支
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}

                    {generating && (
                      <div className="flex gap-4 max-w-3xl">
                        <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center shrink-0 animate-pulse">
                          ...
                        </div>
                        <div className="space-y-1">
                          <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
                          <div className="h-10 w-48 bg-gray-100 rounded-2xl rounded-tl-none animate-pulse" />
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>

              {/* 控制区域 */}
              <div className="p-4 border-t bg-white flex items-center justify-between gap-4">
                <div className="text-sm text-gray-500">
                  {!isFinished ? (
                    <>下一步: <span className="font-medium text-gray-900">执行步骤 #{session.current_round + 1}</span></>
                  ) : (
                    <span className="flex items-center gap-1 text-green-600">
                      <CheckCircle size={14} />
                      对话流程已结束
                    </span>
                  )}
                </div>
                <button
                  onClick={handleNextStep}
                  disabled={isFinished || generating}
                  className="min-w-[140px] bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {generating ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      生成中...
                    </>
                  ) : (
                    <>
                      <Play size={16} />
                      执行下一步
                    </>
                  )}
                </button>
              </div>
            </>
          )}

          {activeTab === 'progress' && enableStepProgress && (
            <div className="p-4 overflow-y-auto">
              <StepProgressDisplay
                sessionId={sessionId}
                compact={false}
                showDetails={true}
                autoRefresh={autoRefresh}
              />
            </div>
          )}

          {activeTab === 'llm' && enableLLMDebug && (
            <div className="p-4 overflow-y-auto">
              <LLMIODisplay
                sessionId={sessionId}
                compact={false}
                showDetails={true}
                autoRefresh={autoRefresh}
                showStreaming={true}
                showDebugInfo={true}
              />
            </div>
          )}

          {activeTab === 'visualization' && enableStepProgress && flowData && (
            <div className="p-4 overflow-y-auto">
              <StepVisualization
                sessionId={sessionId}
                data={flowData}
                showTimeline={true}
                showPerformance={true}
                interactive={true}
              />
            </div>
          )}
        </div>

        {/* 右侧面板 - LLM调试 */}
        {enableLLMDebug && rightPanelExpanded && (
          <div className="w-96 border-l bg-white flex flex-col">
            <div className="flex items-center justify-between p-3 border-b">
              <h3 className="font-medium text-gray-900">LLM调试</h3>
              <div className="flex items-center gap-2">
                {llmStats && (
                  <span className="text-xs text-gray-500">
                    {llmStats.total_interactions} 调用
                  </span>
                )}
                <button
                  onClick={() => setRightPanelExpanded(false)}
                  className="p-1 hover:bg-gray-100 rounded"
                >
                  <ChevronDown className="w-4 h-4 rotate-90" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto">
              <LLMIODisplay
                sessionId={sessionId}
                compact={true}
                showDetails={true}
                autoRefresh={autoRefresh}
                showStreaming={true}
              />
            </div>
          </div>
        )}

        {/* 右侧面板收起按钮 */}
        {enableLLMDebug && !rightPanelExpanded && (
          <div className="w-8 border-l bg-white flex items-center justify-center">
            <button
              onClick={() => setRightPanelExpanded(true)}
              className="p-1 hover:bg-gray-100 rounded"
            >
              <ChevronUp className="w-4 h-4 rotate-270" />
            </button>
          </div>
        )}
      </div>

      {/* 调试面板 */}
      {enableDebugPanel && (
        <DebugPanel
          sessionId={sessionId}
          visible={debugPanelVisible}
          onClose={() => setDebugPanelVisible(false)}
          autoRefresh={autoRefresh}
          size={debugPanelSize}
          position="fixed"
          showAdvanced={true}
        />
      )}
    </div>
  );
};

export default EnhancedSessionTheater;