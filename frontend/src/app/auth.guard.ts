import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs/operators';

import { AuthService } from './services/auth.service';

export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isAuthenticated()) {
    return true;
  }
  return auth.bootstrap().pipe(
    map(user =>
      user
        ? true
        : router.createUrlTree(['/login'], {
            queryParams: { returnUrl: state.url }
          })
    )
  );
};

export const guestGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isAuthenticated()) {
    return router.createUrlTree(['/admin']);
  }
  return auth.bootstrap().pipe(
    map(user => (user ? router.createUrlTree(['/admin']) : true))
  );
};

export const displayGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) {
    return true;
  }
  if (auth.getDisplayError()) {
    return true;
  }

  return auth.bootstrap().pipe(
    map(user => {
      if (user) {
        return true;
      }
      if (auth.getDisplayError()) {
        return true;
      }
      return router.createUrlTree(['/login']);
    })
  );
};
