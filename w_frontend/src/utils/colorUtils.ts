const colorPalette = [
  { tag: "bg-purple-100 text-purple-800", button: "bg-purple-100 text-purple-700 hover:bg-purple-200" },
  { tag: "bg-pink-100 text-pink-800", button: "bg-pink-100 text-pink-700 hover:bg-pink-200" },
  { tag: "bg-green-100 text-green-800", button: "bg-green-100 text-green-700 hover:bg-green-200" },
  { tag: "bg-yellow-100 text-yellow-800", button: "bg-yellow-100 text-yellow-700 hover:bg-yellow-200" },
  { tag: "bg-indigo-100 text-indigo-800", button: "bg-indigo-100 text-indigo-700 hover:bg-indigo-200" },
  { tag: "bg-red-100 text-red-800", button: "bg-red-100 text-red-700 hover:bg-red-200" },
  { tag: "bg-blue-100 text-blue-800", button: "bg-blue-100 text-blue-700 hover:bg-blue-200" },
];

const simpleHash = (str: string): number => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
};

export const getProjectColors = (projectName?: string) => {
  if (!projectName) {
    return { 
      tag: "bg-gray-100 text-gray-800", 
      button: "bg-gray-100 text-gray-700 hover:bg-gray-200" 
    };
  }
  const index = simpleHash(projectName) % colorPalette.length;
  return colorPalette[index];
};

export const blueButtonStyle = "bg-blue-100 text-blue-700 font-semibold hover:bg-blue-200 transition-colors";
export const greenButtonStyle = "bg-green-100 text-green-700 font-semibold hover:bg-green-200 transition-colors";