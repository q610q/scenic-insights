import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { fullscreen: true, title: '数据大屏' },
    },
    {
      path: '/explore',
      name: 'explore',
      component: () => import('@/views/Explore.vue'),
      meta: { title: '筛选探索' },
    },
    {
      path: '/spot/:id',
      name: 'spot-detail',
      component: () => import('@/views/SpotDetail.vue'),
      meta: { title: '景区详情' },
      props: (route) => ({ id: Number(route.params.id) }),
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.afterEach((to) => {
  const t = to.meta?.title as string | undefined
  document.title = t ? `${t} · 旅游数据` : '旅游数据可视化'
})

export default router
