import { useState, useEffect, useContext, createContext, useRef } from 'react';
import {
  Users,
  GitBranch,
  MessageSquare,
  Play,
  Plus,
  Search,
  Trash2,
  Edit3,
  Save,
  X,
  ChevronRight,
  Download,
  CheckCircle,
  ArrowRight,
  FileText,
  Settings,
  RefreshCw,
  CornerDownLeft,
  Lightbulb,
  LogOut,
  RotateCcw,
  Globe,
  Key,
  Bot
} from 'lucide-react';

// --- LLM测试页面组件 ---
import LLMTestPage from './LLMTestPage';

// --- 主题配置系统 ---

type ThemeKey = 'blue' | 'purple' | 'emerald' | 'rose' | 'amber';

interface ThemeConfig {
  name: string;
  primary: string;       // 按钮背景、Sidebar激活
  primaryHover: string;  // 按钮悬停
  text: string;          // 链接文字、图标颜色
  textHover: string;     // 链接悬停
  bgSoft: string;        // 浅色背景 (Card highlight)
  border: string;        // 边框高亮
  ring: string;          // 输入框Focus
  iconBg: string;        // 圆形图标背景
  badge: string;         // Badge 样式
}

const THEMES: Record<ThemeKey, ThemeConfig> = {
  blue: {
    name: '商务蓝',
    primary: 'bg-blue-600',
    primaryHover: 'hover:bg-blue-700',
    text: 'text-blue-600',
    textHover: 'hover:text-blue-800',
    bgSoft: 'bg-blue-50',
    border: 'border-blue-200',
    ring: 'focus:ring-blue-200',
    iconBg: 'bg-blue-500',
    badge: 'bg-blue-100 text-blue-800'
  },
  purple: {
    name: '优雅紫',
    primary: 'bg-purple-600',
    primaryHover: 'hover:bg-purple-700',
    text: 'text-purple-600',
    textHover: 'hover:text-purple-800',
    bgSoft: 'bg-purple-50',
    border: 'border-purple-200',
    ring: 'focus:ring-purple-200',
    iconBg: 'bg-purple-500',
    badge: 'bg-purple-100 text-purple-800'
  },
  emerald: {
    name: '清新绿',
    primary: 'bg-emerald-600',
    primaryHover: 'hover:bg-emerald-700',
    text: 'text-emerald-600',
    textHover: 'hover:text-emerald-800',
    bgSoft: 'bg-emerald-50',
    border: 'border-emerald-200',
    ring: 'focus:ring-emerald-200',
    iconBg: 'bg-emerald-500',
    badge: 'bg-emerald-100 text-emerald-800'
  },
  rose: {
    name: '活力红',
    primary: 'bg-rose-600',
    primaryHover: 'hover:bg-rose-700',
    text: 'text-rose-600',
    textHover: 'hover:text-rose-800',
    bgSoft: 'bg-rose-50',
    border: 'border-rose-200',
    ring: 'focus:ring-rose-200',
    iconBg: 'bg-rose-500',
    badge: 'bg-rose-100 text-rose-800'
  },
  amber: {
    name: '暖阳橙',
    primary: 'bg-amber-600',
    primaryHover: 'hover:bg-amber-700',
    text: 'text-amber-600',
    textHover: 'hover:text-amber-800',
    bgSoft: 'bg-amber-50',
    border: 'border-amber-200',
    ring: 'focus:ring-amber-200',
    iconBg: 'bg-amber-500',
    badge: 'bg-amber-100 text-amber-800'
  }
};

const ThemeContext = createContext<{
  themeKey: ThemeKey;
  theme: ThemeConfig;
  setThemeKey: (k: ThemeKey) => void;
}>({ 
  themeKey: 'blue', 
  theme: THEMES.blue, 
  setThemeKey: () => {} 
});

const useTheme = () => useContext(ThemeContext);

// --- 类型定义 ---

interface Role {
  id: number;
  name: string;
  prompt: string;
  created_at: string;
}

interface FlowStep {
  id: number;
  order: number;
  speaker_role_ref: string;
  target_role_ref?: string;
  task_type: 'ask_question' | 'answer_question' | 'comment' | string;
  context_scope: 'all' | 'last_n_messages';
  context_param?: { n: number };
  logic_config?: {
    next_step_order?: number;
    exit_condition?: string;
    max_loops?: number;
  };
}

interface FlowTemplate {
  id: number;
  name: string;
  topic?: string;
  is_active: boolean;
  steps: FlowStep[];
  created_at: string;
}

interface SessionParticipant {
  session_role_id: number;
  role_ref: string;
  role_id: number;
  role_name: string;
}

interface Session {
  id: number;
  topic: string;
  flow_template_id: number;
  flow_template_name?: string;
  status: 'not_started' | 'running' | 'paused' | 'finished';
  current_step_index: number;
  loop_counters: Record<number, number>;
  participants: SessionParticipant[];
  created_at: string;
  updated_at: string;
}

interface Message {
  id: number;
  session_id: number;
  speaker_session_role_id: number;
  speaker_role_name: string;
  target_session_role_id?: number;
  target_role_name?: string;
  content: string;
  content_summary?: string;
  round_index: number;
  created_at: string;
}

// --- Mock Backend ---

const MOCK_DELAY = 600;

const initialRoles: Role[] = [
  { id: 1, name: "王老师", prompt: "你是一名资深高中物理老师，教学风格循循善诱。", created_at: new Date().toISOString() },
  { id: 2, name: "李同学", prompt: "你是一名好奇心强的高中生，喜欢提问。", created_at: new Date().toISOString() },
  { id: 3, name: "张教授", prompt: "你是一名严谨的大学物理教授。", created_at: new Date().toISOString() },
];

const initialFlows: FlowTemplate[] = [
  {
    id: 1,
    name: "循环教学演示",
    topic: "动量守恒定律在宏观与微观下的适用性。请详细讨论其在不同参照系下的表现，以及在相对论效应显著时的修正公式。",
    is_active: true,
    created_at: new Date().toISOString(),
    steps: [
      { id: 101, order: 1, speaker_role_ref: "王老师", task_type: "ask_question", context_scope: "all", logic_config: { next_step_order: 2 } },
      { id: 102, order: 2, speaker_role_ref: "李同学", target_role_ref: "王老师", task_type: "answer_question", context_scope: "last_n_messages", context_param: { n: 1 } },
      { id: 103, order: 3, speaker_role_ref: "王老师", target_role_ref: "李同学", task_type: "comment", context_scope: "all", logic_config: { next_step_order: 1, exit_condition: "学生回答正确", max_loops: 3 } }
    ]
  }
];

const db = {
  roles: [...initialRoles],
  flows: [...initialFlows],
  sessions: [] as Session[],
  messages: [] as Message[],
};

const api = {
  getRoles: async (params: any = {}) => {
    await new Promise(r => setTimeout(r, MOCK_DELAY));
    let res = [...db.roles];
    if (params.keyword) res = res.filter(r => r.name.includes(params.keyword));
    return { items: res, total: res.length };
  },
  saveRole: async (role: Partial<Role>) => {
    await new Promise(r => setTimeout(r, MOCK_DELAY));
    const isDuplicate = db.roles.some(r => r.name === role.name && r.id !== role.id);
    if (isDuplicate) throw new Error(`角色名称 "${role.name}" 已存在。`);
    if (role.id) {
      const idx = db.roles.findIndex(r => r.id === role.id);
      db.roles[idx] = { ...db.roles[idx], ...role } as Role;
    } else {
      db.roles.push({ ...role, id: Date.now(), created_at: new Date().toISOString() } as Role);
    }
    return true;
  },
  deleteRole: async (id: number) => {
    await new Promise(r => setTimeout(r, MOCK_DELAY));
    db.roles = db.roles.filter(r => r.id !== id);
    return true;
  },
  getFlows: async () => {
    await new Promise(r => setTimeout(r, MOCK_DELAY));
    return { items: db.flows };
  },
  getFlowDetail: async (id: number) => {
    await new Promise(r => setTimeout(r, MOCK_DELAY));
    return db.flows.find(f => f.id === id);
  },
  saveFlow: async (flow: Partial<FlowTemplate>) => {
    await new Promise(r => setTimeout(r, MOCK_DELAY));
    if (flow.id) {
      const idx = db.flows.findIndex(f => f.id === flow.id);
      db.flows[idx] = { ...db.flows[idx], ...flow } as FlowTemplate;
    } else {
      db.flows.push({ ...flow, id: Date.now(), created_at: new Date().toISOString() } as FlowTemplate);
    }
    return true;
  },
  deleteFlow: async (id: number) => {
    await new Promise(r => setTimeout(r, MOCK_DELAY));
    db.flows = db.flows.filter(f => f.id !== id);
    return true;
  },
  getSessions: async (params: any = {}) => {
    await new Promise(r => setTimeout(r, MOCK_DELAY));
    let res = [...db.sessions].sort((a,b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    if (params.status) res = res.filter(s => s.status === params.status);
    return { items: res, total: res.length };
  },
  createSession: async (data: any) => {
    await new Promise(r => setTimeout(r, MOCK_DELAY));
    const template = db.flows.find(f => f.id === Number(data.flow_template_id));
    const participants = data.role_mappings.map((m: any, idx: number) => {
      const role = db.roles.find(r => r.id === Number(m.role_id));
      return {
        session_role_id: 1000 + idx,
        role_ref: m.role_ref,
        role_id: m.role_id,
        role_name: role?.name || 'Unknown'
      };
    });
    const newSession: Session = {
      id: Date.now(),
      topic: data.topic,
      flow_template_id: Number(data.flow_template_id),
      flow_template_name: template?.name,
      status: 'not_started',
      current_step_index: 0,
      loop_counters: {},
      participants,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    db.sessions.push(newSession);
    return newSession;
  },
  getSessionDetail: async (id: number) => {
    await new Promise(r => setTimeout(r, MOCK_DELAY));
    return db.sessions.find(s => s.id === id);
  },
  getSessionMessages: async (id: number) => {
    await new Promise(r => setTimeout(r, MOCK_DELAY));
    return { items: db.messages.filter(m => m.session_id === id) };
  },
  runNextStep: async (sessionId: number) => {
    await new Promise(r => setTimeout(r, 1000));
    const session = db.sessions.find(s => s.id === sessionId);
    if (!session) throw new Error("Session not found");
    const template = db.flows.find(f => f.id === session.flow_template_id);
    if (!template) throw new Error("Template not found");

    if (session.current_step_index >= template.steps.length) {
      session.status = 'finished';
      return { session, is_finished: true, message: null };
    }

    const currentStep = template.steps[session.current_step_index];
    session.loop_counters[session.current_step_index] = (session.loop_counters[session.current_step_index] || 0) + 1;

    const speaker = session.participants.find(p => p.role_ref === currentStep.speaker_role_ref);
    const target = session.participants.find(p => p.role_ref === currentStep.target_role_ref);
    let targetRoleName = target?.role_name;
    if (currentStep.target_role_ref === '__TOPIC__') targetRoleName = '预设议题';

    let mockContent = "";
    if (session.current_step_index === 0 && template.topic) {
      mockContent = `[开场] ${speaker?.role_name} 针对议题 "${template.topic.substring(0, 30)}..." 发言：\n各位好，今天我们来讨论这个话题。我认为...`;
    } else {
      const targetStr = targetRoleName ? ` 对 ${targetRoleName}` : '';
      mockContent = `[模拟生成] ${speaker?.role_name}${targetStr} 说: ... (基于 Step ${currentStep.order} - ${currentStep.task_type})`;
    }

    const newMessage: Message = {
      id: Date.now(),
      session_id: session.id,
      speaker_session_role_id: speaker?.session_role_id || 0,
      speaker_role_name: speaker?.role_name || 'System',
      target_session_role_id: target?.session_role_id,
      target_role_name: targetRoleName,
      content: mockContent,
      round_index: session.current_step_index + 1,
      created_at: new Date().toISOString()
    };
    db.messages.push(newMessage);
    session.status = 'running';

    let nextIndex = session.current_step_index + 1;
    if (currentStep.logic_config) {
      const { next_step_order, max_loops } = currentStep.logic_config;
      const currentLoopCount = session.loop_counters[session.current_step_index];
      if (max_loops && currentLoopCount >= max_loops) {
        nextIndex = session.current_step_index + 1;
      } else if (next_step_order) {
        const jumpToIndex = template.steps.findIndex(s => s.order === next_step_order);
        if (jumpToIndex !== -1) nextIndex = jumpToIndex;
      }
    }
    session.current_step_index = nextIndex;
    if (session.current_step_index >= template.steps.length) {
      session.status = 'finished';
    }
    return { session, message: newMessage, is_finished: session.status === 'finished' };
  },
  finishSession: async (id: number) => {
    await new Promise(r => setTimeout(r, MOCK_DELAY));
    const session = db.sessions.find(s => s.id === id);
    if (session) session.status = 'finished';
    return true;
  }
};

// --- UI Components ---

const Button = ({ children, onClick, variant = 'primary', className = '', disabled = false, icon: Icon, size = 'md' }: any) => {
  const { theme } = useTheme();
  
  const baseStyle = "rounded-lg font-medium transition-all flex items-center justify-center gap-2";
  const sizes: any = {
    xs: "px-2.5 py-1 text-xs",
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2"
  };
  
  // Dynamic class construction based on theme
  const variants: any = {
    primary: `${theme.primary} text-white ${theme.primaryHover} disabled:bg-gray-300`,
    secondary: "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:bg-gray-100",
    danger: "bg-red-50 text-red-600 hover:bg-red-100",
    ghost: "text-gray-600 hover:bg-gray-100",
  };

  return (
    <button 
      onClick={onClick} 
      disabled={disabled}
      className={`${baseStyle} ${sizes[size]} ${variants[variant]} ${className}`}
    >
      {Icon && <Icon size={size === 'sm' || size === 'xs' ? 14 : 18} />}
      {children}
    </button>
  );
};

const Card = ({ children, className = '', title, actions }: any) => (
  <div className={`bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden ${className}`}>
    {(title || actions) && (
      <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
        <h3 className="font-semibold text-gray-800">{title}</h3>
        <div className="flex gap-2">{actions}</div>
      </div>
    )}
    <div className="p-6">{children}</div>
  </div>
);

const Badge = ({ children, color = 'theme' }: any) => {
  const { theme } = useTheme();
  
  // Custom theme badge or semantic colors
  let colorClass = "";
  if (color === 'theme') colorClass = theme.badge;
  else if (color === 'green') colorClass = "bg-green-100 text-green-800";
  else if (color === 'gray') colorClass = "bg-gray-100 text-gray-800";
  else if (color === 'red') colorClass = "bg-red-100 text-red-800";
  else colorClass = "bg-blue-100 text-blue-800"; // fallback

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {children}
    </span>
  );
};

const Modal = ({ isOpen, onClose, title, children, footer }: any) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
      <div className="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl animate-in fade-in zoom-in duration-200">
        <div className="px-6 py-4 border-b flex justify-between items-center">
          <h3 className="text-lg font-bold">{title}</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X size={20} /></button>
        </div>
        <div className="p-6 overflow-y-auto flex-1">{children}</div>
        {footer && <div className="px-6 py-4 border-t bg-gray-50 rounded-b-xl flex justify-end gap-3">{footer}</div>}
      </div>
    </div>
  );
};

const EmptyState = ({ message, action }: any) => (
  <div className="flex flex-col items-center justify-center py-16 text-gray-500">
    <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
      <Search size={24} className="text-gray-400" />
    </div>
    <p className="mb-4">{message}</p>
    {action}
  </div>
);

// --- Pages ---

// 1. Role Management
const RoleManagement = () => {
  const { theme } = useTheme();
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Partial<Role>>({});

  const fetchRoles = async () => {
    setLoading(true);
    const res = await api.getRoles();
    setRoles(res.items);
    setLoading(false);
  };

  useEffect(() => { fetchRoles(); }, []);

  const handleSave = async () => {
    try {
      if (!editingRole.name || !editingRole.prompt) {
        alert("请填写角色名称和提示词");
        return;
      }
      await api.saveRole(editingRole);
      setIsModalOpen(false);
      fetchRoles();
    } catch (e: any) {
      alert(e.message || "保存失败");
    }
  };

  const handleDelete = async (id: number) => {
    if (confirm("确认删除该角色吗？")) {
      await api.deleteRole(id);
      fetchRoles();
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">角色管理</h1>
          <p className="text-gray-500 text-sm mt-1">创建角色并定义其核心 Prompt</p>
        </div>
        <Button onClick={() => { setEditingRole({}); setIsModalOpen(true); }} icon={Plus}>新建角色</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {roles.map(role => (
          <Card key={role.id} className={`hover:shadow-md transition-shadow hover:border-${theme.name === '商务蓝' ? 'blue' : 'gray'}-300`}>
            <div className="flex justify-between items-center h-full">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold ${theme.iconBg}`}>
                  {role.name[0]}
                </div>
                <div>
                  <h3 className="font-bold text-gray-900">{role.name}</h3>
                </div>
              </div>
              <div className="flex gap-1">
                <button 
                  onClick={() => { setEditingRole(role); setIsModalOpen(true); }} 
                  className={`p-2 text-gray-400 ${theme.textHover} hover:bg-gray-50 rounded-full transition-colors`}
                >
                  <Edit3 size={18} />
                </button>
                <button 
                  onClick={() => handleDelete(role.id)} 
                  className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-full transition-colors"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          </Card>
        ))}
        {roles.length === 0 && !loading && (
          <div className="col-span-full py-10">
            <EmptyState message="暂无角色，请点击右上角新建" />
          </div>
        )}
      </div>

      <Modal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        title={editingRole.id ? "编辑角色" : "新建角色"}
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>取消</Button>
            <Button onClick={handleSave}>保存</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">角色名称 <span className="text-red-500">*</span></label>
            <input 
              className={`w-full border rounded-lg px-3 py-2 ${theme.ring}`}
              value={editingRole.name || ''} 
              onChange={e => setEditingRole({...editingRole, name: e.target.value})}
              placeholder="请输入唯一角色名称"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">角色提示词 (Prompt) <span className="text-red-500">*</span></label>
            <textarea 
              className={`w-full border rounded-lg px-3 py-2 h-40 ${theme.ring}`}
              value={editingRole.prompt || ''}
              onChange={e => setEditingRole({...editingRole, prompt: e.target.value})}
              placeholder="请输入角色的设定、风格、行为准则等提示词..."
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

// 2. Flow Templates
const FlowManagement = () => {
  const { theme } = useTheme();
  const [flows, setFlows] = useState<FlowTemplate[]>([]);
  const [editingFlow, setEditingFlow] = useState<Partial<FlowTemplate> | null>(null);

  useEffect(() => {
    api.getFlows().then(res => setFlows(res.items));
  }, [editingFlow]); 

  const handleCreate = () => {
    setEditingFlow({ name: "新对话流程", topic: "", is_active: true, steps: [] });
  };

  const handleEdit = async (flow: FlowTemplate) => {
    const detail = await api.getFlowDetail(flow.id);
    setEditingFlow(detail || null);
  }

  if (editingFlow) {
    return <FlowEditor flow={editingFlow} onSave={async (flow: any) => {
      await api.saveFlow(flow);
      setEditingFlow(null);
    }} onCancel={() => setEditingFlow(null)} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">流程模板</h1>
          <p className="text-gray-500 text-sm mt-1">设计对话的SOP（标准作业程序）</p>
        </div>
        <Button onClick={handleCreate} icon={Plus}>新建模板</Button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600">模板名称</th>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600">议题</th>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600">步骤数</th>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600">状态</th>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {flows.map(flow => (
              <tr key={flow.id} className="hover:bg-gray-50/50">
                <td className="px-6 py-4 font-medium text-gray-900">{flow.name}</td>
                <td className="px-6 py-4 text-gray-600 max-w-xs truncate">{flow.topic || '-'}</td>
                <td className="px-6 py-4 text-gray-600">{flow.steps?.length || 0}</td>
                <td className="px-6 py-4">
                  <Badge color={flow.is_active ? 'green' : 'gray'}>{flow.is_active ? '启用' : '禁用'}</Badge>
                </td>
                <td className="px-6 py-4 text-right">
                  <button onClick={() => handleEdit(flow)} className={`${theme.text} ${theme.textHover} font-medium text-sm`}>编辑</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {flows.length === 0 && <EmptyState message="暂无流程模板" />}
      </div>
    </div>
  );
};

// Flow Editor Sub-component
const FlowEditor = ({ flow, onSave, onCancel }: any) => {
  const { theme } = useTheme();
  const [data, setData] = useState(flow);
  const [steps, setSteps] = useState<FlowStep[]>(flow.steps || []);
  const [roles, setRoles] = useState<Role[]>([]);
  const [expandedLogicStep, setExpandedLogicStep] = useState<number | null>(null);

  useEffect(() => {
    api.getRoles().then(res => setRoles(res.items));
  }, []);

  const addStep = () => {
    const newStep: FlowStep = {
      id: Date.now(),
      order: steps.length + 1,
      speaker_role_ref: roles[0]?.name || '', 
      task_type: 'ask_question',
      context_scope: 'all'
    };
    setSteps([...steps, newStep]);
  };

  const updateStep = (index: number, field: string, value: any) => {
    const newSteps = [...steps];
    newSteps[index] = { ...newSteps[index], [field]: value };
    setSteps(newSteps);
  };

  const updateLogicConfig = (index: number, field: string, value: any) => {
    const newSteps = [...steps];
    const currentLogic = newSteps[index].logic_config || {};
    newSteps[index].logic_config = { ...currentLogic, [field]: value };
    setSteps(newSteps);
  };

  const deleteStep = (index: number) => {
    const newSteps = steps.filter((_, i) => i !== index).map((s, i) => ({ ...s, order: i + 1 }));
    setSteps(newSteps);
  };

  return (
    <div className="space-y-6 animate-in slide-in-from-right duration-300">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={onCancel} className="p-2 hover:bg-gray-100 rounded-full"><ArrowRight className="rotate-180" /></button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{data.id ? '编辑模板' : '新建模板'}</h1>
        </div>
        <div className="ml-auto flex gap-3">
          <Button variant="secondary" onClick={onCancel}>取消</Button>
          <Button onClick={() => onSave({ ...data, steps })} icon={Save}>保存模板</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="基本信息" className="h-fit">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">模板名称</label>
              <input className={`w-full border rounded-lg px-3 py-2 ${theme.ring}`} value={data.name} onChange={e => setData({...data, name: e.target.value})} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                <Lightbulb size={14} className="text-yellow-500"/> 预设议题 (Topic)
              </label>
              <textarea 
                className={`w-full border rounded-lg px-3 py-2 bg-yellow-50/50 border-yellow-200 focus:ring-yellow-200 h-48`}
                placeholder="例如：动量守恒的适用条件..."
                value={data.topic || ''} 
                onChange={e => setData({...data, topic: e.target.value})} 
              />
              <p className="text-xs text-gray-500 mt-1">若填写，会话的第一位发言者将针对此议题开场。</p>
            </div>
          </div>
        </Card>

        <div className="lg:col-span-2 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-gray-800">流程步骤 ({steps.length})</h3>
            <Button size="sm" onClick={addStep} icon={Plus}>添加步骤</Button>
          </div>
          
          <div className="space-y-3">
            {steps.map((step, index) => {
              const isLogicExpanded = expandedLogicStep === index;
              return (
              <div key={step.id} className="bg-white border border-gray-200 rounded-lg p-4 relative group hover:border-gray-300 transition-colors">
                <div className="flex items-start gap-4">
                  <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center font-bold text-gray-500 shrink-0 mt-1">
                    {index + 1}
                  </div>
                  
                  <div className="flex-1 space-y-3">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">发言者 (Speaker)</label>
                        <select 
                          className={`w-full border rounded px-2 py-1 text-sm ${theme.bgSoft} font-medium ${theme.text} ${theme.ring}`}
                          value={step.speaker_role_ref}
                          onChange={e => updateStep(index, 'speaker_role_ref', e.target.value)}
                        >
                          <option value="">选择角色...</option>
                          {roles.map(r => <option key={r.id} value={r.name}>{r.name}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">任务类型</label>
                        <select 
                          className={`w-full border rounded px-2 py-1 text-sm ${theme.ring}`}
                          value={step.task_type}
                          onChange={e => updateStep(index, 'task_type', e.target.value)}
                        >
                          <option value="ask_question">提问</option>
                          <option value="answer_question">回答</option>
                          <option value="comment">点评</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">对象 (Target)</label>
                        <select 
                          className={`w-full border rounded px-2 py-1 text-sm bg-gray-50 ${theme.ring}`}
                          value={step.target_role_ref || ''}
                          onChange={e => updateStep(index, 'target_role_ref', e.target.value)}
                        >
                          <option value="">(无对象/系统)</option>
                          <option value="__TOPIC__">预设议题 (Topic)</option>
                          {roles.map(r => <option key={r.id} value={r.name}>{r.name}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">上下文策略</label>
                        <select 
                          className={`w-full border rounded px-2 py-1 text-sm ${theme.ring}`}
                          value={step.context_scope}
                          onChange={e => updateStep(index, 'context_scope', e.target.value)}
                        >
                          <option value="all">全部历史</option>
                          <option value="last_n_messages">最近 N 条</option>
                        </select>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 text-xs">
                       <button 
                         onClick={() => setExpandedLogicStep(isLogicExpanded ? null : index)}
                         className={`flex items-center gap-1 px-2 py-1 rounded border transition-colors ${
                           isLogicExpanded 
                             ? `${theme.bgSoft} ${theme.border} ${theme.text}` 
                             : step.logic_config?.next_step_order ? `${theme.bgSoft} ${theme.border} ${theme.text}` : 'bg-gray-50 border-gray-200 text-gray-500'
                         }`}
                       >
                         <Settings size={12} />
                         {isLogicExpanded ? '收起流转配置' : '流转逻辑配置'}
                         {step.logic_config?.next_step_order && !isLogicExpanded && (
                           <span className="ml-1 font-bold">→ 跳转至 Step {step.logic_config.next_step_order}</span>
                         )}
                       </button>
                    </div>

                    {isLogicExpanded && (
                      <div className={`p-3 rounded border ${theme.bgSoft} ${theme.border} grid grid-cols-1 md:grid-cols-3 gap-4 animate-in fade-in slide-in-from-top-2 duration-200`}>
                        <div>
                           <label className={`text-xs font-bold ${theme.text} block mb-1 flex items-center gap-1`}>
                             <CornerDownLeft size={12}/> 跳转逻辑 (Next Step)
                           </label>
                           <select 
                             className={`w-full border ${theme.border} rounded px-2 py-1 text-sm`}
                             value={step.logic_config?.next_step_order || ''}
                             onChange={e => updateLogicConfig(index, 'next_step_order', e.target.value ? Number(e.target.value) : undefined)}
                           >
                             <option value="">默认 (继续下一步)</option>
                             {steps.map(s => (
                               <option key={s.id} value={s.order}>Step {s.order} ({s.speaker_role_ref})</option>
                             ))}
                           </select>
                        </div>
                        <div>
                           <label className={`text-xs font-bold ${theme.text} block mb-1 flex items-center gap-1`}>
                             <FileText size={12}/> 循环结束条件
                           </label>
                           <input 
                             className={`w-full border ${theme.border} rounded px-2 py-1 text-sm`}
                             placeholder="例如：学生回答正确"
                             value={step.logic_config?.exit_condition || ''}
                             onChange={e => updateLogicConfig(index, 'exit_condition', e.target.value)}
                           />
                        </div>
                        <div>
                           <label className={`text-xs font-bold ${theme.text} block mb-1 flex items-center gap-1`}>
                             <RefreshCw size={12}/> 最大循环次数
                           </label>
                           <input 
                             type="number"
                             className={`w-full border ${theme.border} rounded px-2 py-1 text-sm`}
                             placeholder="例如：3"
                             value={step.logic_config?.max_loops || ''}
                             onChange={e => updateLogicConfig(index, 'max_loops', e.target.value ? Number(e.target.value) : undefined)}
                           />
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <button onClick={() => deleteStep(index)} className="p-2 text-gray-300 hover:text-red-500 transition-colors">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            )})}
            {steps.length === 0 && <div className="text-center py-10 text-gray-400 border-2 border-dashed border-gray-200 rounded-lg">暂无步骤，请点击添加</div>}
          </div>
        </div>
      </div>
    </div>
  );
};

// 3. Session Management & Theater
const SessionManagement = ({ onPlayback }: any) => {
  const { theme } = useTheme();
  const [view, setView] = useState<'list' | 'create' | 'theater'>('list');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);

  useEffect(() => {
    if (onPlayback) {
      setActiveSessionId(onPlayback);
      setView('theater');
    }
  }, [onPlayback]);

  useEffect(() => {
    if (view === 'list') {
      api.getSessions().then(res => setSessions(res.items));
    }
  }, [view]);

  if (view === 'create') {
    return <SessionCreator onCancel={() => setView('list')} onSuccess={(id: number) => { setActiveSessionId(id); setView('theater'); }} />;
  }

  if (view === 'theater' && activeSessionId) {
    return <SessionTheater sessionId={activeSessionId} onExit={() => { setView('list'); setActiveSessionId(null); }} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">会话管理</h1>
          <p className="text-gray-500 text-sm mt-1">创建并执行多角色对话剧场</p>
        </div>
        <Button onClick={() => setView('create')} icon={Plus}>新建会话</Button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600">主题</th>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600">模板</th>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600">状态</th>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600">创建时间</th>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sessions.map(s => (
              <tr key={s.id} className="hover:bg-gray-50/50">
                <td className="px-6 py-4 font-medium text-gray-900">{s.topic}</td>
                <td className="px-6 py-4 text-gray-600">{s.flow_template_name}</td>
                <td className="px-6 py-4">
                  <Badge color={s.status === 'running' ? 'green' : s.status === 'finished' ? 'gray' : 'theme'}>
                    {s.status === 'running' ? '进行中' : s.status === 'finished' ? '已结束' : '未开始'}
                  </Badge>
                </td>
                <td className="px-6 py-4 text-gray-500 text-sm">{new Date(s.created_at).toLocaleDateString()}</td>
                <td className="px-6 py-4 text-right">
                  <button onClick={() => { setActiveSessionId(s.id); setView('theater'); }} className={`${theme.text} ${theme.textHover} font-medium text-sm flex items-center gap-1 justify-end ml-auto`}>
                    {s.status === 'finished' ? '回放' : '进入剧场'} <ChevronRight size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {sessions.length === 0 && <EmptyState message="暂无会话记录" />}
      </div>
    </div>
  );
};

const SessionCreator = ({ onCancel, onSuccess }: any) => {
  const { theme } = useTheme();
  const [formData, setFormData] = useState({ topic: '', flow_template_id: '', role_mappings: [] as any[] });
  const [flows, setFlows] = useState<FlowTemplate[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [requiredRoles, setRequiredRoles] = useState<string[]>([]);

  useEffect(() => {
    api.getFlows().then(res => setFlows(res.items));
    api.getRoles().then(res => setRoles(res.items));
  }, []);

  useEffect(() => {
    if (formData.flow_template_id) {
      const flow = flows.find(f => f.id === Number(formData.flow_template_id));
      if (flow) {
        const refs = Array.from(new Set(flow.steps.map(s => s.speaker_role_ref).filter(Boolean)));
        setRequiredRoles(refs);
        if (flow.topic) setFormData(prev => ({ ...prev, topic: flow.topic || '' }));
        setFormData(prev => ({
          ...prev,
          role_mappings: refs.map(ref => {
            const matchedRole = roles.find(r => r.name === ref);
            return { role_ref: ref, role_id: matchedRole ? matchedRole.id : '' };
          })
        }));
      }
    }
  }, [formData.flow_template_id, flows, roles]);

  const updateMapping = (ref: string, roleId: string) => {
    setFormData(prev => ({
      ...prev,
      role_mappings: prev.role_mappings.map(m => m.role_ref === ref ? { ...m, role_id: roleId } : m)
    }));
  };

  const handleCreate = async () => {
    if (!formData.topic || !formData.flow_template_id || formData.role_mappings.some(m => !m.role_id)) {
      alert("请填写完整信息");
      return;
    }
    const session = await api.createSession(formData);
    onSuccess(session.id);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 py-6">
      <div className="flex items-center gap-4 border-b pb-4">
        <button onClick={onCancel} className="p-2 hover:bg-gray-100 rounded-full"><ArrowRight className="rotate-180" /></button>
        <h1 className="text-2xl font-bold text-gray-900">发起新会话</h1>
      </div>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">会话主题</label>
          <input className={`w-full border rounded-lg px-3 py-2 ${theme.ring}`} placeholder="例如：高中物理-动量守恒教学" value={formData.topic} onChange={e => setFormData({...formData, topic: e.target.value})} />
          <p className="text-xs text-gray-500 mt-1">若所选模板包含预设议题，此处会自动填充。</p>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">选择流程模板</label>
          <select className={`w-full border rounded-lg px-3 py-2 ${theme.ring}`} value={formData.flow_template_id} onChange={e => setFormData({...formData, flow_template_id: e.target.value})}>
            <option value="">请选择...</option>
            {flows.map(f => <option key={f.id} value={f.id}>{f.name} ({f.steps.length}步)</option>)}
          </select>
        </div>

        {requiredRoles.length > 0 && (
          <div className={`p-4 rounded-lg border ${theme.bgSoft} ${theme.border}`}>
            <h3 className={`font-bold ${theme.text} mb-3 flex items-center gap-2`}><Users size={18}/> 角色映射 (Casting)</h3>
            <div className="space-y-3">
              {requiredRoles.map(ref => (
                <div key={ref} className="flex items-center gap-4">
                  <div className={`w-24 text-sm font-medium ${theme.text} text-right`}>
                    {ref} <span className="opacity-50">→</span>
                  </div>
                  <select 
                    className={`flex-1 border rounded px-3 py-2 text-sm ${theme.ring}`}
                    value={formData.role_mappings.find(m => m.role_ref === ref)?.role_id || ''}
                    onChange={e => updateMapping(ref, e.target.value)}
                  >
                    <option value="">选择扮演该角色的实例...</option>
                    {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </div>
              ))}
            </div>
            <p className={`text-xs ${theme.text} mt-2 opacity-70`}>* 系统已尝试根据名称自动匹配角色</p>
          </div>
        )}

        <div className="flex justify-end gap-3 pt-4">
          <Button variant="secondary" onClick={onCancel}>取消</Button>
          <Button onClick={handleCreate} disabled={!formData.topic}>创建并进入</Button>
        </div>
      </div>
    </div>
  );
};

const SessionTheater = ({ sessionId, onExit }: any) => {
  const { theme } = useTheme();
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [generating, setGenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadData = async () => {
    const s = await api.getSessionDetail(sessionId);
    setSession(s || null);
    const m = await api.getSessionMessages(sessionId);
    setMessages(m.items);
  };

  useEffect(() => { loadData(); }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, generating]);

  const handleNextStep = async () => {
    if (!session) return;
    setGenerating(true);
    try {
      const res = await api.runNextStep(session.id);
      setSession(res.session);
      if (res.message) {
        setMessages(prev => [...prev, res.message]);
      }
    } catch (e) {
      alert("执行失败");
    } finally {
      setGenerating(false);
    }
  };

  const handleFinish = async () => {
    if (confirm("确定要结束当前会话吗？")) {
      await api.finishSession(sessionId);
      loadData();
    }
  };

  if (!session) return <div className="p-10 text-center">Loading Theater...</div>;

  const isFinished = session.status === 'finished';

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col bg-gray-100 rounded-xl overflow-hidden border border-gray-300 shadow-2xl">
      <div className="bg-white border-b px-6 py-3 flex justify-between items-center shrink-0 z-10">
        <div className="flex items-center gap-4">
          <button onClick={onExit} className="p-2 hover:bg-gray-100 rounded-full"><ArrowRight className="rotate-180" /></button>
          <div>
            <h2 className="font-bold text-gray-900 flex items-center gap-2">
              {session.topic} 
              <Badge color={isFinished ? 'gray' : 'green'}>{isFinished ? '已结束' : '进行中'}</Badge>
            </h2>
            <div className="text-xs text-gray-500 mt-0.5 flex gap-2">
              <span>Template: {session.flow_template_name}</span>
              <span>•</span>
              <span>Step Order: {session.current_step_index + 1}</span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" icon={Download} />
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-64 bg-gray-50 border-r p-4 overflow-y-auto hidden md:flex md:flex-col justify-between">
          <div className="space-y-3 flex-1 overflow-y-auto">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">Cast Members</h3>
            {session.participants.map(p => (
              <div key={p.session_role_id} className="bg-white p-3 rounded-lg border shadow-sm flex items-center gap-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm
                  ${p.role_ref.includes('老师') || p.role_ref === 'teacher' ? theme.iconBg : 'bg-green-500'}`}>
                  {p.role_name[0]}
                </div>
                <div>
                  <div className="font-bold text-sm text-gray-900">{p.role_name}</div>
                  <div className="text-xs text-gray-500">as {p.role_ref}</div>
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
               const isTeacher = session.participants.find(p => p.role_name === msg.speaker_role_name)?.role_ref.includes('老师');
               // Dynamic bubble color for teacher
               const roleColor = isTeacher ? `${theme.bgSoft} ${theme.text}` : 'bg-gray-100 text-gray-900';
               return (
                <div key={msg.id} className={`flex gap-4 max-w-3xl`}>
                  <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center shrink-0 font-bold text-gray-600 text-sm">
                    {msg.speaker_role_name[0]}
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
                      <button className={`text-xs ${theme.text} hover:underline flex items-center gap-1`}><GitBranch size={10} /> 创建分支</button>
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
                   <>下一步: <span className="font-medium text-gray-900">执行预设步骤 #{session.current_step_index + 1}</span></>
                ) : (
                   <span className="flex items-center gap-1 text-green-600"><CheckCircle size={14}/> 对话流程已结束</span>
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

// 4. History Page
const HistoryPage = ({ onPlayback }: any) => {
  const { theme } = useTheme();
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    api.getSessions({ status: 'finished' }).then(res => setSessions(res.items));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">历史记录</h1>
          <p className="text-gray-500 text-sm mt-1">查看已结束的对话存档</p>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600">主题</th>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600">模板</th>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600">结束时间</th>
              <th className="px-6 py-4 text-sm font-semibold text-gray-600 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sessions.map(s => (
              <tr key={s.id} className="hover:bg-gray-50/50">
                <td className="px-6 py-4 font-medium text-gray-900">{s.topic}</td>
                <td className="px-6 py-4 text-gray-600">{s.flow_template_name}</td>
                <td className="px-6 py-4 text-gray-500 text-sm">{new Date(s.updated_at).toLocaleString()}</td>
                <td className="px-6 py-4 text-right">
                  <button onClick={() => onPlayback(s.id)} className={`${theme.text} ${theme.textHover} font-medium text-sm flex items-center gap-1 justify-end ml-auto`}>
                    回放 <ChevronRight size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {sessions.length === 0 && <EmptyState message="暂无历史记录" />}
      </div>
    </div>
  );
};

// 5. Settings Page (Updated with Theme Switcher)
const SettingsPage = () => {
  const { themeKey, setThemeKey } = useTheme();

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">系统设置</h1>
          <p className="text-gray-500 text-sm mt-1">配置系统参数与偏好</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 max-w-2xl">
        {/* Theme Settings */}
        <Card title="主题外观">
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {Object.keys(THEMES).map((key) => {
                const k = key as ThemeKey;
                const t = THEMES[k];
                return (
                  <button
                    key={k}
                    onClick={() => setThemeKey(k)}
                    className={`flex flex-col items-center gap-2 p-3 rounded-lg border-2 transition-all ${
                      themeKey === k ? `${t.border} ${t.bgSoft}` : 'border-transparent hover:bg-gray-50'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-full ${t.primary} shadow-sm`}></div>
                    <span className="text-xs font-medium text-gray-700">{t.name}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </Card>

        <Card title="基础设置">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-2">
                <Globe size={16} /> 界面语言
              </label>
              <select className="w-full border rounded-lg px-3 py-2 bg-gray-50">
                <option>简体中文</option>
                <option>English</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-2">
                <Key size={16} /> LLM API Key
              </label>
              <input type="password" className="w-full border rounded-lg px-3 py-2" placeholder="sk-........................" />
              <p className="text-xs text-gray-500 mt-1">用于连接大模型服务的密钥</p>
            </div>
          </div>
        </Card>

        <Card title="数据管理">
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-red-50 border border-red-100 rounded-lg">
              <div>
                <h4 className="font-bold text-red-800 text-sm">重置所有数据</h4>
                <p className="text-xs text-red-600 mt-1">这将清空所有角色、模板和历史记录，不可恢复。</p>
              </div>
              <Button variant="danger" size="sm" icon={RotateCcw}>立即重置</Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

// --- Main App ---
const App = () => {
  const [activeTab, setActiveTab] = useState('roles');
  const [playbackSessionId, setPlaybackSessionId] = useState<number | null>(null);
  
  // State for Theme
  const [themeKey, setThemeKey] = useState<ThemeKey>('blue');
  const theme = THEMES[themeKey];

  const handlePlayback = (id: number) => {
    setPlaybackSessionId(id);
    setActiveTab('sessions');
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'roles': return <RoleManagement />;
      case 'flows': return <FlowManagement />;
      case 'sessions': return <SessionManagement onPlayback={playbackSessionId} />;
      case 'llm-test': return <LLMTestPage theme={themeKey} />;
      case 'history': return <HistoryPage onPlayback={handlePlayback} />;
      case 'settings': return <SettingsPage />;
      default: return <RoleManagement />;
    }
  };

  return (
    <ThemeContext.Provider value={{ themeKey, theme, setThemeKey }}>
      <div className="flex h-screen w-full bg-gray-100 text-gray-900 font-sans">
        <div className="w-64 bg-slate-900 text-white flex flex-col shrink-0 transition-colors">
          <div className="p-6">
            <div className="flex items-center gap-3 font-bold text-xl tracking-tight">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${theme.iconBg} text-white`}>
                <MessageSquare size={18} />
              </div>
              MultiRole
            </div>
            <div className="text-xs text-slate-400 mt-1">多角色对话仿真系统</div>
          </div>
          <nav className="flex-1 px-4 space-y-2">
            <NavItem icon={Users} label="角色管理" active={activeTab === 'roles'} onClick={() => setActiveTab('roles')} />
            <NavItem icon={GitBranch} label="流程模板" active={activeTab === 'flows'} onClick={() => setActiveTab('flows')} />
            <NavItem icon={Play} label="会话剧场" active={activeTab === 'sessions'} onClick={() => setActiveTab('sessions')} />
            <NavItem icon={Bot} label="LLM测试" active={activeTab === 'llm-test'} onClick={() => setActiveTab('llm-test')} />
            <div className="pt-4 mt-4 border-t border-slate-700">
              <NavItem icon={FileText} label="历史记录" active={activeTab === 'history'} onClick={() => setActiveTab('history')} />
              <NavItem icon={Settings} label="系统设置" active={activeTab === 'settings'} onClick={() => setActiveTab('settings')} />
            </div>
          </nav>
          <div className="p-4 bg-slate-800 m-4 rounded-lg">
            <div className="text-xs text-slate-400 mb-2">当前状态</div>
            <div className="flex items-center gap-2 text-sm">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              Mock Server Online
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto p-8">
            {renderContent()}
          </div>
        </div>
      </div>
    </ThemeContext.Provider>
  );
};

const NavItem = ({ icon: Icon, label, active, onClick }: any) => {
  const { theme } = useTheme();
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all
        ${active ? `${theme.primary} text-white shadow-lg shadow-blue-900/20` : 'text-slate-300 hover:bg-slate-800 hover:text-white'}`}
    >
      <Icon size={18} />
      {label}
    </button>
  );
};

export default App;