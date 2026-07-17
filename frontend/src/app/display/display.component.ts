import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-display',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.Default,
  templateUrl: './display.component.html',
  styleUrl: './display.component.css'
})
export class DisplayComponent {

  private readonly auth = inject(AuthService);

  get displayError(): string | null {
    const err = this.auth.getDisplayError();
    if (err === 'token_invalid') {
      return 'Token inválido o revocado';
    }
    if (err === 'session_expired') {
      return 'Sesión caducada';
    }
    return null;
  }

  get showContent(): boolean {
    return !this.displayError && this.auth.isAuthenticated();
  }
}
