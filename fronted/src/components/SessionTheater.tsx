import React, { useState, useEffect, useRef } from 'react';
import { ArrowRight, Download, Play, CheckCircle, LogOut, GitBranch } from 'lucide-react';
import { sessionApi } from '../api/sessionApi';
import { Session, Message } from '../api/sessionApi';
import { useTheme } from '../theme';

interface SessionTheaterProps {
  sessionId: number;
  onExit: () => void;
}

const SessionTheater: React.FC<SessionTheaterProps> = ({ sessionId, onExit }) => {
  const { theme } = useTheme();
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [generating, setGenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadData = async () => {
    try {
      const s = await sessionApi.getSession(sessionId);
      setSession(s || null);
      const m = await sessionApi.getMessages(sessionId);
      setMessages(m.items);
    } catch (error) {
      console.error('Failed to load session data:', error);
    }
  };

  useEffect(() => { loadData(); }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, generating]);

  const handleNextStep = async () => {
    if (!session) return;
    setGenerating(true);
    try {
      const res = await sessionApi.executeNextStep(session.id);
      if (res.message) {
        setMessages(prev => [...prev, res.message]);
      }
      // Reload session data to get updated state
      const updatedSession = await sessionApi.getSession(session.id);
      setSession(updatedSession);
    } catch (e) {
      alert("执行失败");
    } finally {
      setGenerating(false);
    }
  };

  const handleFinish = async () => {
    if (confirm("确定要结束当前会话吗？")) {
      await sessionApi.terminateSession(sessionId);
      loadData();
    }
  };

  if (!session) return <div className="p-10 text-center">Loading Theater...</div>;

  const isFinished = session.status === 'finished';
  const templateName = session.flow_snapshot?.name || 'Unknown Template';
  const participants = session.session_roles || [];

  // Badge component
  const Badge = ({ color, children }: { color: string; children: React.ReactNode }) => (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
      color === 'gray' ? 'bg-gray-100 text-gray-600' :
      color === 'green' ? 'bg-green-100 text-green-600' :
      'bg-blue-100 text-blue-600'
    }`}>
      {children}
    </span>
  );

  // Button component
  const Button = ({
    onClick,
    disabled,
    children,
    icon: Icon,
    variant = 'primary',
    size = 'md',
    className = ''
  }: {
    onClick?: () => void;
    disabled?: boolean;
    children: React.ReactNode;
    icon?: any;
    variant?: 'primary' | 'ghost' | 'danger';
    size?: 'sm' | 'md' | 'xs';
    className?: string;
  }) => {
    const baseClasses = 'inline-flex items-center gap-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500';
    const variants = {
      primary: `${theme.primary} text-white hover:${theme.primaryHover} disabled:opacity-50`,
      ghost: 'hover:bg-gray-100 text-gray-600',
      danger: 'bg-red-500 text-white hover:bg-red-600'
    };
    const sizes = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-sm',
      xs: 'px-2 py-1 text-xs'
    };

    return (
      <button
        onClick={onClick}
        disabled={disabled}
        className={`${baseClasses} ${variants[variant]} ${sizes[size]} ${className}`}
      >
        {Icon && <Icon size={16} />}
        {children}
      </button>
    );
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col bg-gray-100 rounded-xl overflow-hidden border border-gray-300 shadow-2xl">
      <div className="bg-white border-b px-6 py-3 flex justify-between items-center shrink-0 z-10">
        <div className="flex items-center gap-4">
          <button onClick={onExit} className="p-2 hover:bg-gray-100 rounded-full">
            <ArrowRight className="rotate-180" />
          </button>
          <div>
            <h2 className="font-bold text-gray-900 flex items-center gap-2">
              {session.topic}
              <Badge color={isFinished ? 'gray' : 'green'}>
                {isFinished ? '已结束' : '进行中'}
              </Badge>
            </h2>
            <div className="text-xs text-gray-500 mt-0.5 flex gap-2">
              <span>Template: {templateName}</span>
              <span>•</span>
              <span>Steps: {session.executed_steps_count}</span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" icon={Download}>下载</Button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-64 bg-gray-50 border-r p-4 overflow-y-auto hidden md:flex md:flex-col justify-between">
          <div className="space-y-3 flex-1 overflow-y-auto">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">Cast Members</h3>
            {participants.map(p => (
              <div key={p.id} className="bg-white p-3 rounded-lg border shadow-sm flex items-center gap-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm
                  ${p.role_ref.includes('老师') || p.role_ref === 'teacher' ? theme.iconBg : 'bg-green-500'}`}>
                  {p.role_ref[0]?.toUpperCase() || 'R'}
                </div>
                <div>
                  <div className="font-bold text-sm text-gray-900">{p.role_ref}</div>
                  <div className="text-xs text-gray-500">ID: {p.role_id}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="pt-4 border-t mt-4 shrink-0">
             {!isFinished && (
               <Button
                 variant="danger"
                 size="xs"
                 onClick={handleFinish}
                 icon={LogOut}
                 className="w-full justify-center"
               >
                 结束会话
               </Button>
             )}
          </div>
        </div>

        <div className="flex-1 bg-white flex flex-col relative">
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.length === 0 && (
              <div className="text-center text-gray-400 py-20">
                <p>舞台已就绪，等待开场...</p>
              </div>
            )}

            {messages.map(msg => {
               const isTeacher = msg.speaker_role_name?.includes('老师') || false;
               // Dynamic bubble color for teacher
               const roleColor = isTeacher ? `${theme.bgSoft} ${theme.text}` : 'bg-gray-100 text-gray-900';
               return (
                <div key={msg.id} className={`flex gap-4 max-w-3xl`}>
                  <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center shrink-0 font-bold text-gray-600 text-sm">
                    {msg.speaker_role_name?.[0]?.toUpperCase() || '?'}
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-baseline gap-2">
                      <span className="font-bold text-sm text-gray-900">{msg.speaker_role_name}</span>
                      <span className="text-xs text-gray-400">{new Date(msg.created_at).toLocaleTimeString()}</span>
                      {msg.target_role_name && <span className="text-xs text-gray-400">to {msg.target_role_name}</span>}
                    </div>
                    <div className={`px-4 py-3 rounded-2xl rounded-tl-none ${roleColor} text-sm leading-relaxed shadow-sm`}>
                      {msg.content}
                    </div>
                    <div className="flex gap-2 opacity-0 hover:opacity-100 transition-opacity">
                      <button className={`text-xs ${theme.text} hover:underline flex items-center gap-1`}>
                        <GitBranch size={10} /> 创建分支
                      </button>
                    </div>
                  </div>
                </div>
               );
            })}

            {generating && (
              <div className="flex gap-4 max-w-3xl">
                <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center shrink-0 animate-pulse">...</div>
                <div className="space-y-1">
                  <div className="h-4 w-20 bg-gray-100 rounded animate-pulse"/>
                  <div className="h-10 w-48 bg-gray-100 rounded-2xl rounded-tl-none animate-pulse"/>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="p-4 border-t bg-white flex items-center justify-between gap-4">
             <div className="text-sm text-gray-500">
                {!isFinished ? (
                   <>下一步: <span className="font-medium text-gray-900">执行预设步骤 (已执行 {session.executed_steps_count} 步)</span></>
                ) : (
                   <span className="flex items-center gap-1 text-green-600">
                     <CheckCircle size={14}/> 对话流程已结束
                   </span>
                )}
             </div>
             <Button
               onClick={handleNextStep}
               disabled={isFinished || generating}
               className="min-w-[140px]"
               icon={Play}
             >
               {generating ? '生成中...' : '执行下一步'}
             </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SessionTheater;