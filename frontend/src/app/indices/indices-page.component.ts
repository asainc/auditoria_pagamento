/** Estado de atualização é consultado no servidor; não há sucesso presumido. */
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subscription, exhaustMap, firstValueFrom, takeWhile, timer } from 'rxjs';
import { IndexApiService } from '../core/index-api.service';
import { ApiConfiguration } from '../core/config';
import { IndexOption, IndexStatus } from '../core/contracts';
import { Notifications } from '../core/notifications';

@Component({selector:'app-indices-page', standalone:true, imports:[FormsModule], template:`
  <main class="management-page"><header class="management-heading"><div><span class="eyebrow">Séries de referência</span><h1>Gestão dos índices</h1><p>Consulte os índices disponíveis e acompanhe a atualização das planilhas.</p></div><button type="button" class="primary" (click)="update()" [disabled]="busy()">{{ busy() ? 'Atualizando…' : 'Verificar e atualizar' }}</button></header>
    <section class="management-card index-status"><span class="status-dot" [class.success]="status()?.estado === 'atualizado'"></span><div><h2>{{ stateLabel() }}</h2><p>{{ status()?.mensagem ?? 'Consultando o serviço de índices…' }}</p>@if (status()?.atualizado_em; as updated) {<small>Última tentativa: {{ updated }}</small>}</div></section>
    <section class="management-card"><div class="panel-heading"><h2>Índices disponíveis <span class="count">{{ options().length }}</span></h2><label class="search-field">Buscar índice<input [ngModel]="query()" (ngModelChange)="query.set($event)" placeholder="Nome ou chave"></label></div>
      <div class="index-grid">@for (index of filtered(); track index.chave) {<div class="index-item"><strong>{{ index.nome }}</strong><small>{{ index.chave }}</small></div>} @empty {<p>Nenhum índice encontrado.</p>}</div>
    </section>
    @if (status(); as current) {<details class="management-card checksums"><summary>Identificação das planilhas utilizadas</summary><p>Os códigos identificam o conteúdo dos arquivos. Não comprovam, por si só, a atualidade das séries.</p>@for (entry of hashes(); track entry.name) {<div><strong>{{ entry.name }}</strong><code>{{ entry.hash }}</code></div>}</details>}
  </main>
`})
export class IndicesPageComponent {
  private readonly api = inject(IndexApiService);
  private readonly notifications = inject(Notifications);
  private readonly config = inject(ApiConfiguration);
  private readonly destroy = inject(DestroyRef);
  private polling: Subscription | null = null;
  readonly status = signal<IndexStatus | null>(null);
  readonly options = signal<IndexOption[]>([]);
  readonly query = signal('');
  readonly busy = signal(false);
  readonly filtered = computed(() => this.options().filter(item => `${item.chave} ${item.nome}`.toLocaleLowerCase('pt-BR').includes(this.query().toLocaleLowerCase('pt-BR'))));
  readonly hashes = computed(() => Object.entries(this.status()?.arquivos_sha256 ?? {}).map(([name,hash]) => ({name,hash})));
  readonly stateLabel = computed(() => ({nao_verificado:'Atualidade ainda não verificada',atualizado:'Atualização verificada',falha:'Atualização não confirmada',executando:'Atualização em andamento'}[this.status()?.estado ?? 'nao_verificado']));
  constructor() {void this.load();}
  async load(): Promise<void> {try {const [status, options] = await Promise.all([firstValueFrom(this.api.status()), firstValueFrom(this.api.options())]);this.status.set(status);this.options.set(options);if (status.estado === 'executando') this.watch();} catch(error) {this.notifications.error(error);}}
  async update(): Promise<void> {this.busy.set(true);try {this.status.set(await firstValueFrom(this.api.update()));this.watch();} catch(error) {this.busy.set(false);this.notifications.error(error);}}
  /** A assinatura é encerrada na navegação e nos estados finais. */
  private watch(): void {
    this.busy.set(true); this.polling?.unsubscribe();
    this.polling = timer(0,this.config.pollInterval).pipe(exhaustMap(() => this.api.status()),takeWhile(status => status.estado === 'executando',true),takeUntilDestroyed(this.destroy)).subscribe({next:status => {this.status.set(status);this.busy.set(status.estado === 'executando');},error:error => {this.busy.set(false);this.notifications.error(error);}});
  }
}
