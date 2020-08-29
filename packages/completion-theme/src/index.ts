import { Signal } from '@lumino/signaling';
import { kernelIcon, LabIcon } from '@jupyterlab/ui-components';
import { ICommandPalette, IThemeManager } from '@jupyterlab/apputils';
import { JupyterFrontEndPlugin } from '@jupyterlab/application';

import {
  ICompletionIconSet,
  ICompletionTheme,
  ILSPCompletionThemeManager,
  PLUGIN_ID,
  COMPLETER_THEME_PREFIX,
  KernelKind
} from './types';

export class CompletionThemeManager implements ILSPCompletionThemeManager {
  protected current_icons: Map<string, LabIcon>;
  protected themes: Map<string, ICompletionTheme>;
  private current_theme_id: string;
  private icons_cache: Map<string, LabIcon>;
  private _current_theme_changed: Signal<ILSPCompletionThemeManager, void>;

  constructor(protected themeManager: IThemeManager) {
    this._current_theme_changed = new Signal(this);
    this.themes = new Map();
    this.icons_cache = new Map();
    themeManager.themeChanged.connect(this.update_icons_set, this);
  }

  get current_theme_changed() {
    return this._current_theme_changed;
  }

  protected is_theme_light() {
    const current = this.themeManager.theme;
    if (!current) {
      // assume true by default
      return true;
    }
    return this.themeManager.isLight(current);
  }

  theme_ids() {
    return [...this.themes.keys()];
  }

  get_current_theme_id() {
    return this.current_theme_id;
  }

  get_theme(id: string) {
    return this.themes.get(id);
  }

  get_iconset(theme: ICompletionTheme): Map<keyof ICompletionIconSet, LabIcon> {
    const icons_sets = theme.icons;
    const dark_mode_and_dark_supported =
      !this.is_theme_light() && typeof icons_sets.dark !== 'undefined';
    const set: ICompletionIconSet = dark_mode_and_dark_supported
      ? icons_sets.dark
      : icons_sets.light;
    const icons: Map<keyof ICompletionIconSet, LabIcon> = new Map();
    const mode = this.is_theme_light() ? 'light' : 'dark';
    for (let [completion_kind, svg] of Object.entries(set)) {
      let name =
        'lsp:' + theme.id + '-' + completion_kind.toLowerCase() + '-' + mode;
      let icon: LabIcon;
      if (this.icons_cache.has(name)) {
        icon = this.icons_cache.get(name);
      } else {
        icon = new LabIcon({
          name: name,
          svgstr: svg
        });
        this.icons_cache.set(name, icon);
      }
      icons.set(completion_kind as keyof ICompletionIconSet, icon);
    }
    return icons;
  }

  protected update_icons_set() {
    if (this.current_theme === null) {
      return;
    }
    this.current_icons = this.get_iconset(this.current_theme);
  }

  get_icon(type: string): LabIcon {
    if (this.current_theme === null) {
      return null;
    }
    let options = this.current_theme.icons.options || {};
    if (type) {
      type =
        type.substring(0, 1).toUpperCase() + type.substring(1).toLowerCase();
    }
    if (this.current_icons.has(type)) {
      return this.current_icons.get(type).bindprops(options);
    }
    if (type === KernelKind) {
      return kernelIcon;
    }
    return null;
  }

  protected get current_theme_class() {
    return COMPLETER_THEME_PREFIX + this.current_theme_id;
  }

  set_theme(id: string | null) {
    if (this.current_theme_id) {
      document.body.classList.remove(this.current_theme_class);
    }
    if (!this.themes.has(id)) {
      console.warn(
        `[LSP][Completer] Icons theme ${id} cannot be set yet (it may be loaded later).`
      );
    }
    this.current_theme_id = id;
    document.body.classList.add(this.current_theme_class);
    this.update_icons_set();
    this._current_theme_changed.emit(void 0);
  }

  protected get current_theme(): ICompletionTheme | null {
    if (this.themes.has(this.current_theme_id)) {
      return this.themes.get(this.current_theme_id);
    }
    return null;
  }

  register_theme(theme: ICompletionTheme) {
    if (this.themes.has(theme.id)) {
      console.warn(
        'Theme with name',
        theme.id,
        'was already registered, overwriting.'
      );
    }
    this.themes.set(theme.id, theme);
    this.update_icons_set();
  }
}

export const COMPLETION_THEME_MANAGER: JupyterFrontEndPlugin<ILSPCompletionThemeManager> = {
  id: PLUGIN_ID,
  requires: [IThemeManager, ICommandPalette],
  activate: (app, themeManager: IThemeManager) => {
    let manager = new CompletionThemeManager(themeManager);
    return manager;
  },
  provides: ILSPCompletionThemeManager,
  autoStart: true
};
