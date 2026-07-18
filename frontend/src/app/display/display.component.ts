import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  inject,
} from '@angular/core';

import { AuthService } from '../services/auth.service';
import { DisplayStateService } from '../services/display-state.service';
import { QrPanelComponent } from './qr-panel.component';
import { QueueStripComponent } from './queue-strip.component';
import { YoutubePlayerComponent } from './youtube-player.component';

@Component({
  selector: 'app-display',
  standalone: true,
  imports: [
    CommonModule,
    YoutubePlayerComponent,
    QrPanelComponent,
    QueueStripComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './display.component.html',
  styleUrl: './display.component.css',
})
export class DisplayComponent implements OnInit {

  private readonly auth = inject(AuthService);
  readonly displayState = inject(DisplayStateService);

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

  ngOnInit(): void {
    if (this.showContent) {
      void this.displayState.start();
    }
  }

  onVideoEnded(): void {
    void this.displayState.advancePlayback();
  }
}
