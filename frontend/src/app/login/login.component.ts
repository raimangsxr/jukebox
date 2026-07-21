import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize } from 'rxjs/operators';

import { AuthService } from '../services/auth.service';

const SAFE_DEFAULT_RETURN = '/admin';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.Default,
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent {

  username = '';
  password = '';
  errorMessage: string | null = null;
  submitting = false;

  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly cdr = inject(ChangeDetectorRef);

  submit(): void {
    this.errorMessage = null;
    if (!this.username.trim() || !this.password) {
      this.errorMessage = 'Introduce usuario y contraseña.';
      return;
    }
    this.submitting = true;
    this.auth
      .login(this.username.trim(), this.password)
      .pipe(
        finalize(() => {
          this.submitting = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: () => {
          const target = this.safeReturnUrl();
          this.router.navigateByUrl(target);
        },
        error: (err: HttpErrorResponse) => {
          if (err.status === 401) {
            this.errorMessage = 'Credenciales inválidas.';
          } else if (err.status === 422) {
            this.errorMessage = 'Revisa los campos.';
          } else {
            this.errorMessage = 'No se pudo conectar con el servidor.';
          }
        }
      });
  }

  private safeReturnUrl(): string {
    const raw = this.route.snapshot.queryParamMap.get('returnUrl');
    if (!raw) {
      return SAFE_DEFAULT_RETURN;
    }
    if (!raw.startsWith('/') || raw.startsWith('//')) {
      return SAFE_DEFAULT_RETURN;
    }
    if (raw === '/login' || raw.startsWith('/login?') || raw.startsWith('/login/')) {
      return SAFE_DEFAULT_RETURN;
    }
    return raw;
  }
}
