/** Notificações podem ser fechadas e não carregam HTML do backend. */
import { Injectable, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { connectionMessage } from './api-errors';

interface Notice {id: number; message: string; kind: 'error' | 'info';}

@Injectable({providedIn: 'root'})
export class Notifications {
  readonly items = signal<Notice[]>([]);
  private sequence = 0;
  show(message: string, kind: Notice['kind'] = 'info'): void {
    this.items.update(items => [...items.slice(-3), {id: ++this.sequence, message, kind}]);
  }
  dismiss(id: number): void { this.items.update(items => items.filter(item => item.id !== id)); }
  /** Converte falhas HTTP em orientação, incluindo campos apontados pela API. */
  error(error: unknown): void {
    let message = 'A operação não foi concluída. Tente novamente.';
    if (error instanceof HttpErrorResponse) {
      if (error.status === 0 || [502,503,504].includes(error.status) || (error.status === 500 && !error.error?.detail)) message = connectionMessage(error.status);
      else if (typeof error.error?.detail === 'string') {
        message = error.error.detail;
        if (Array.isArray(error.error?.campos)) message += ' ' + error.error.campos.map((item: {campo: string; mensagem: string}) => `${item.campo}: ${item.mensagem}`).join('; ');
      }
    } else if (error instanceof Error) message = error.message;
    this.show(message, 'error');
  }
}

/** Revoga URLs temporárias após o navegador iniciar o download. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url; anchor.download = filename; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
