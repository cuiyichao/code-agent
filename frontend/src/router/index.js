import { createRouter, createWebHistory } from 'vue-router';
import ProjectList from '../views/ProjectList.vue';
import NewProject from '../views/NewProject.vue';
import ProjectDetail from '../views/ProjectDetail.vue';

const routes = [
  {
    path: '/',
    name: 'ProjectList',
    component: ProjectList
  },
  {
    path: '/new',
    name: 'NewProject',
    component: NewProject
  },
  {
    path: '/projects/:id',
    name: 'ProjectDetail',
    component: ProjectDetail,
    props: true
  },
  { path: '/projects/:id/analysis', name: 'ProjectAnalysis', component: () => import('@/views/ProjectAnalysis.vue') }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
});

export default router;