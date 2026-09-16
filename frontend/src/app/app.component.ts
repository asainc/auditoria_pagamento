/** Shell Angular único com navegação entre aplicações e módulos operacionais. */
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { NotificationsComponent } from './shared/notifications.component';

type ApplicationKey = 'auditoria' | 'bjn' | 'ai-ready';

type ApplicationDescriptor = {
  key: ApplicationKey;
  label: string;
  subtitle: string;
  route: string;
  badge: string;
};

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, RouterOutlet, NotificationsComponent],
  template: `
    <div class="application-shell" [class.nav-collapsed]="navigationCollapsed()">
      <aside class="platform-sidebar" [class.collapsed]="navigationCollapsed()" aria-label="Aplicações do sistema">
        <div class="platform-sidebar-header">
          <button
            type="button"
            class="sidebar-toggle global-toggle"
            (click)="toggleNavigation()"
            [attr.aria-expanded]="!navigationCollapsed()"
            aria-controls="platform-nav"
            aria-label="Expandir ou retrair aplicações"
          >☰</button>
          @if (!navigationCollapsed()) {
            <div class="platform-branding">
              <span class="brand-mark" aria-hidden="true"></span>
              <div>
                <strong>Plataforma jurídica</strong>
                <small>Aplicações operacionais</small>
              </div>
            </div>
          }
        </div>

        <nav id="platform-nav" class="platform-nav">
          @for (application of applications; track application.key) {
            <a
              [routerLink]="application.route"
              routerLinkActive="active"
              [routerLinkActiveOptions]="{ exact: false }"
              class="platform-link"
              [attr.title]="application.label"
            >
              <span class="platform-link-badge" aria-hidden="true">{{ application.badge }}</span>
              @if (!navigationCollapsed()) {
                <span class="platform-link-copy">
                  <strong>{{ application.label }}</strong>
                  <small>{{ application.subtitle }}</small>
                </span>
              }
            </a>
          }
        </nav>
      </aside>

      <div class="application-content-shell">
        <header class="application-bar">
          <div class="application-bar-main">
            <a class="brand brand--app" [routerLink]="brandRoute()">
              <span class="brand-mark" aria-hidden="true"></span>
              <span class="brand-copy">
                <small>Aplicação</small>
                <strong>{{ activeApplication().label }}</strong>
              </span>
            </a>

            @if (showOperationalNavigation()) {
              <nav aria-label="Navegação principal" class="top-level-nav">
                <a routerLink="/auditoria-pagamentos/calculo" routerLinkActive="active">Cálculo</a>
                <a routerLink="/auditoria-pagamentos/lotes" routerLinkActive="active">Execução em lote</a>
                <a routerLink="/auditoria-pagamentos/indices" routerLinkActive="active">Índices</a>
              </nav>
            } @else {
              <div class="top-level-nav top-level-nav--placeholder">
                <span>{{ activeApplication().subtitle }}</span>
              </div>
            }
          </div>

          <span class="product-context">{{ headerContext() }}</span>
        </header>

        <app-notifications />

        <div class="route-content">
          <router-outlet />
        </div>
      </div>
    </div>
  `,
})
export class AppComponent {
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly navigationCollapsed = signal(false);
  readonly currentUrl = signal(this.router.url);

  readonly applications: ApplicationDescriptor[] = [
    {
      key: 'auditoria',
      label: 'Auditoria de Pagamentos',
      subtitle: 'Aplicação atual',
      route: '/auditoria-pagamentos/calculo',
      badge: 'AP',
    },
    {
      key: 'bjn',
      label: 'BJN',
      subtitle: 'Template de projeto',
      route: '/bjn',
      badge: 'BJ',
    },
    {
      key: 'ai-ready',
      label: 'AI Ready',
      subtitle: 'Template de projeto',
      route: '/ai-ready',
      badge: 'AI',
    },
  ];

  readonly activeApplication = computed<ApplicationDescriptor>(() => {
    const url = this.currentUrl();
    if (url.startsWith('/bjn')) {
      return this.applications[1];
    }
    if (url.startsWith('/ai-ready')) {
      return this.applications[2];
    }
    return this.applications[0];
  });

  readonly showOperationalNavigation = computed(() => this.currentUrl().startsWith('/auditoria-pagamentos'));
  readonly headerContext = computed(() => this.showOperationalNavigation() ? 'Débitos judiciais' : 'Template preparado para expansão');

  constructor() {
    this.router.events
      .pipe(
        filter((event): event is NavigationEnd => event instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(event => this.currentUrl.set(event.urlAfterRedirects));
  }

  toggleNavigation(): void {
    this.navigationCollapsed.set(!this.navigationCollapsed());
  }

  brandRoute(): string {
    return this.activeApplication().route;
  }
}
