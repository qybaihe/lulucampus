/** Frontend-safe copy of demo electives (mirrors agents/_electives DEMO). */
export const DEMO_ELECTIVES = [
  {
    code: 'GE2101',
    title: '批判性思维与表达',
    category: '通识选修',
    credits: 2,
    campus: '珠海校区',
    college: '通识教育部',
    capacity: 120,
    remaining: 18,
    weekday: '周二',
    time: '19:00-20:40',
    teacher: '李老师',
    tags: ['写作', '表达'],
    selectable: true,
  },
  {
    code: 'CS3208',
    title: '移动应用开发',
    category: '专业选修',
    credits: 3,
    campus: '珠海校区',
    college: '计算机学院',
    capacity: 80,
    remaining: 6,
    weekday: '周四',
    time: '14:00-16:35',
    teacher: '王老师',
    tags: ['iOS', 'Swift', '工程实践'],
    selectable: true,
  },
  {
    code: 'ART1102',
    title: '摄影基础',
    category: '通识选修',
    credits: 2,
    campus: '南校园',
    college: '传播与设计学院',
    capacity: 40,
    remaining: 0,
    weekday: '周六',
    time: '09:00-11:30',
    teacher: '陈老师',
    tags: ['艺术', '实践'],
    selectable: false,
  },
  {
    code: 'PE1205',
    title: '羽毛球（提高）',
    category: '体育选修',
    credits: 1,
    campus: '珠海校区',
    college: '体育部',
    capacity: 30,
    remaining: 4,
    weekday: '周三',
    time: '16:20-17:50',
    teacher: '赵老师',
    tags: ['体育', '羽毛球'],
    selectable: true,
  },
  {
    code: 'ECO2301',
    title: '行为经济学导论',
    category: '跨专业选修',
    credits: 2,
    campus: '南校园',
    college: '岭南学院',
    capacity: 60,
    remaining: 22,
    weekday: '周一',
    time: '18:30-20:10',
    teacher: '周老师',
    tags: ['经济', '社科'],
    selectable: true,
  },
  {
    code: 'AI4002',
    title: '大模型应用实践',
    category: '专业选修',
    credits: 2,
    campus: '珠海校区',
    college: '计算机学院',
    capacity: 50,
    remaining: 11,
    weekday: '周五',
    time: '14:00-15:40',
    teacher: '刘老师',
    tags: ['AI', 'Agent', '工程'],
    selectable: true,
  },
] satisfies Array<{
  code: string;
  title: string;
  category: string;
  credits: number;
  campus?: string;
  college?: string;
  capacity?: number;
  remaining?: number;
  weekday?: string;
  time?: string;
  teacher?: string;
  tags?: string[];
  selectable?: boolean;
}>;
