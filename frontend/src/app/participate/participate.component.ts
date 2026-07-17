import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'app-participate',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './participate.component.html',
  styleUrl: './participate.component.css'
})
export class ParticipateComponent {}
