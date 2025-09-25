/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontSize: {
        // 自定義字體大小 - 擴展現有的
        xs: "19px", // 原本是 12px
        sm: "19px", // 原本是 14px
        base: "19px", // 原本是 16px
        lg: "19px", // 原本是 18px
        xl: "20px", // 原本是 20px
        "2xl": "24px", // 原本是 24px
        // 或者添加新的自定義大小
        content: "16px", // 專門用於內容的自定義大小
      },
    },
  },
  plugins: [],
};
