import { Routes } from '@angular/router';

import { AdminComponent } from './admin/admin.component';
import { authGuard, displayGuard, guestGuard } from './auth.guard';
import { DisplayComponent } from './display/display.component';
import { LoginComponent } from './login/login.component';
import { NotFoundComponent } from './not-found/not-found.component';
import { ParticipateComponent } from './participate/participate.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent, canActivate: [guestGuard] },
  { path: 'admin', component: AdminComponent, canActivate: [authGuard] },
  { path: 'participar', component: ParticipateComponent },
  { path: '', component: DisplayComponent, canActivate: [displayGuard] },
  { path: '**', component: NotFoundComponent }
];
