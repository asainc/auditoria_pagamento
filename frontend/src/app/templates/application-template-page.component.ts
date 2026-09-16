/** Página template reutilizável para aplicações futuras do sistema. */
import { Component, computed, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

@Component({
  selector: 'app-template-page',
  standalone: true,
  imports: [RouterLink],
  template: `
    <main class="management-page template-page">
      <header class="management-heading">
        <div>
          <span class="eyebrow">Template de aplicação</span>
          <h1>{{ title() }}</h1>
          <p>{{ description() }}</p>
        </div>
        <a class="button" routerLink="/auditoria-pagamentos/calculo">Abrir Auditoria de Pagamentos</a>
      </header>

      <section class="management-card template-hero">
        <div class="template-hero-badge">{{ initials() }}</div>
        <div>
          <h2>{{ stage() }}</h2>
          <p>
            Esta página já segue a identidade visual da aplicação atual e pode receber jornadas,
            dashboards, automações, relatórios e integrações específicas conforme o projeto evoluir.
          </p>
        </div>
      </section>

      <section class="template-grid">
        <article class="management-card template-card">
          <div class="panel-heading">
            <div>
              <h2>Objetivo do template</h2>
              <p>Estrutura pronta para acelerar novas entregas.</p>
            </div>
          </div>
          <div class="template-card-body">
            <ul>
              <li>Área principal para componentes do projeto.</li>
              <li>Espaço para indicadores, listas, formulários e fluxos operacionais.</li>
              <li>Base pronta para integração com serviços FastAPI já existentes.</li>
            </ul>
          </div>
        </article>

        <article class="management-card template-card">
          <div class="panel-heading">
            <div>
              <h2>Próximos passos sugeridos</h2>
              <p>Itens que podem orientar a evolução do projeto.</p>
            </div>
          </div>
          <div class="template-card-body">
            <ol>
              <li>Definir objetivos e público operacional da aplicação.</li>
              <li>Mapear telas, dados de entrada e saídas esperadas.</li>
              <li>Conectar os endpoints e construir os componentes específicos.</li>
            </ol>
          </div>
        </article>
      </section>
    </main>
  `,
})
export class ApplicationTemplatePageComponent {
  private readonly route = inject(ActivatedRoute);

  readonly title = computed(() => String(this.route.snapshot.data['title'] ?? 'Nova aplicação'));
  readonly description = computed(() => String(this.route.snapshot.data['description'] ?? 'Template reutilizável para aplicações futuras.'));
  readonly initials = computed(() => String(this.route.snapshot.data['initials'] ?? 'TP'));
  readonly stage = computed(() => String(this.route.snapshot.data['stage'] ?? 'Template em preparação'));
}
