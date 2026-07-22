import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-not-found',
  standalone: true,
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <p class="text-xs uppercase tracking-[0.2em] text-jukebox-muted">Error 404</p>
      <h1 class="text-3xl font-bold text-jukebox-primary">Página no encontrada</h1>
      <p class="max-w-md text-sm text-jukebox-muted">
        La página que buscas no existe o se ha movido.
      </p>
      <a
        routerLink="/"
        class="rounded-lg bg-jukebox-accent px-4 py-2 text-sm font-semibold text-white"
      >
        Volver a la pantalla principal
      </a>
    </main>
  `,
})
export class NotFoundComponent {}
