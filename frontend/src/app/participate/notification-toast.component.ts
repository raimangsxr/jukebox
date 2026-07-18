import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';

import { NotificationToastService } from '../services/notification-toast.service';

@Component({
  selector: 'app-notification-toast',
  standalone: true,
  imports: [AsyncPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './notification-toast.component.html',
  styleUrl: './notification-toast.component.css'
})
export class NotificationToastComponent {
  readonly toastService = inject(NotificationToastService);

  dismiss(): void {
    this.toastService.dismiss();
  }
}
