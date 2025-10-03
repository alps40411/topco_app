// frontend/src/utils/quillConfig.ts

// 共用的 Quill 工具列配置
export const quillModules = {
  toolbar: [
    ["bold", "italic", "underline", "strike"],
    [{ list: "ordered" }, { list: "bullet" }],
    ["link", "image", "paperclip"],
    ["clean"],
  ],
};

// 共用的 Quill 格式配置
export const quillFormats = [
  "header",
  "bold",
  "italic",
  "underline",
  "strike",
  "list",
  "bullet",
  "color",
  "background",
  "link",
  "image",
];
