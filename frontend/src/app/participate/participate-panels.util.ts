export type ParticipatePanelId = 'votes' | 'submit' | 'mySongs';

export const PARTICIPATE_PANEL_DEFAULTS: Record<ParticipatePanelId, boolean> = {
  votes: true,
  submit: false,
  mySongs: false,
};
