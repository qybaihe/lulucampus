import type { LocalContextPayload } from './types';
import { DEMO_ELECTIVES } from './demoElectives';

export const DEMO_LOCAL_CONTEXT: LocalContextPayload = {
  campusHint: '珠海校区',
  timezone: 'Asia/Shanghai',
  preferredWindows: ['18:00-21:00', '14:00-16:00'],
  timetable: [
    {
      id: 'c1',
      title: '软件工程',
      day: '2026-08-13',
      start: '09:00',
      end: '11:30',
      location: '海琴 3 号楼',
    },
    {
      id: 'c2',
      title: '算法设计',
      day: '2026-08-13',
      start: '14:00',
      end: '15:40',
      location: '教学楼 A201',
    },
    {
      id: 'c3',
      title: '组会',
      day: '2026-08-14',
      start: '10:00',
      end: '12:00',
      location: '实验室',
    },
  ],
  tasks: [
    {
      id: 't1',
      title: '补交离散作业',
      due: '2026-08-13T21:00:00+08:00',
      status: 'todo',
    },
    {
      id: 't2',
      title: '体育馆健身',
      due: '2026-08-13T20:00:00+08:00',
      status: 'todo',
      notes: '想约南校园新体育馆健身房',
    },
  ],
  electiveCatalog: DEMO_ELECTIVES,
};
