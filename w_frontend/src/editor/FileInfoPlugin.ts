// w_frontend/src/editor/FileInfoPlugin.ts

import { Plugin, ButtonView } from "ckeditor5";

// 與現有 Quill 版本相同的 info circle SVG 圖示
const FILEINFO_ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle fill="none" stroke="currentColor" stroke-width="2" cx="12" cy="12" r="10"/><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M12 16v-4"/><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M12 8h.01"/></svg>`;

/**
 * 建立檔案格式資訊按鈕 Plugin 的工廠函式
 * 點擊後開啟 FileTypeModal
 */
export function createFileInfoPlugin(openModal: () => void) {
  return class FileInfoPluginClass extends Plugin {
    static get pluginName() {
      return "FileInfoPlugin" as const;
    }

    init() {
      const editor = this.editor;

      editor.ui.componentFactory.add("fileinfo", (locale) => {
        const buttonView = new ButtonView(locale);

        buttonView.set({
          label: "支援 34 種檔案格式（點擊查看完整列表）",
          icon: FILEINFO_ICON,
          tooltip: true,
        });

        buttonView.on("execute", () => {
          openModal();
        });

        return buttonView;
      });
    }
  };
}
