/** Cada aplicação fica agrupada para permitir expansão futura do sistema. */
import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'auditoria-pagamentos',
    children: [
      {
        path: 'calculo',
        loadComponent: () => import('./calculation/calculation-page.component').then(module => module.CalculationPageComponent),
      },
      {
        path: 'historico',
        loadComponent: () => import('./history/calculation-history-page.component').then(module => module.CalculationHistoryPageComponent),
      },
      {
        path: 'lotes',
        loadComponent: () => import('./batches/batch-page.component').then(module => module.BatchPageComponent),
      },
      {
        path: 'indices',
        loadComponent: () => import('./indices/indices-page.component').then(module => module.IndicesPageComponent),
      },
      { path: '', pathMatch: 'full', redirectTo: 'calculo' },
    ],
  },
  {
    path: 'bjn',
    loadComponent: () => import('./templates/application-template-page.component').then(module => module.ApplicationTemplatePageComponent),
    data: {
      title: 'BJN',
      description: 'Página template preparada para receber novos fluxos, dashboards, integrações e componentes específicos do projeto BJN.',
      initials: 'BJ',
      stage: 'Template em preparação',
    },
  },
  {
    path: 'ai-ready',
    loadComponent: () => import('./templates/application-template-page.component').then(module => module.ApplicationTemplatePageComponent),
    data: {
      title: 'AI Ready',
      description: 'Página template preparada para futuras jornadas de IA, monitoramento operacional, checklists e experiências guiadas.',
      initials: 'AI',
      stage: 'Template em preparação',
    },
  },
  { path: '', pathMatch: 'full', redirectTo: 'auditoria-pagamentos/calculo' },
  { path: '**', redirectTo: 'auditoria-pagamentos/calculo' },
];
