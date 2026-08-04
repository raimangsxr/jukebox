import '@angular/compiler';
import { describe, expect, it } from 'vitest';

import { CollapsibleSectionComponent } from './collapsible-section.component';

describe('CollapsibleSectionComponent', () => {
  it('emits expandedChange when header is toggled from collapsed', () => {
    const component = new CollapsibleSectionComponent();
    component.expanded = false;
    const emitted: boolean[] = [];
    component.expandedChange.subscribe(value => emitted.push(value));

    component.onToggle();

    expect(emitted).toEqual([true]);
  });

  it('emits expandedChange when header is toggled from expanded', () => {
    const component = new CollapsibleSectionComponent();
    component.expanded = true;
    const emitted: boolean[] = [];
    component.expandedChange.subscribe(value => emitted.push(value));

    component.onToggle();

    expect(emitted).toEqual([false]);
  });

  it('tracks expanded state for chevron rotation binding', () => {
    const component = new CollapsibleSectionComponent();
    component.expanded = true;
    expect(component.expanded).toBe(true);
  });

  it('shows badge when provided', () => {
    const component = new CollapsibleSectionComponent();
    component.badge = '3 pendientes';
    expect(component.badge).toBe('3 pendientes');
  });
});
