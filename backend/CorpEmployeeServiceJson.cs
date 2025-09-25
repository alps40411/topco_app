using System;
using System.Collections.Generic;
using System.IO;
using System.Configuration;
using Newtonsoft.Json;

namespace CorpEmployeeServiceJson
{
    class Program
    {
        static void Main(string[] args)
        {
            try
            {
                // 設定控制台編碼為 UTF-8
                Console.OutputEncoding = System.Text.Encoding.UTF8;

                // 調用 MyReport.dll 中的 CorpEmployeeService.loadForward
                var myReportAssembly = System.Reflection.Assembly.LoadFrom("MyReport.dll");
                var corpEmployeeServiceType = myReportAssembly.GetType("MyReport.Services.CorpEmployeeService");

                if (corpEmployeeServiceType == null)
                {
                    OutputError("找不到 MyReport.Services.CorpEmployeeService 類別");
                    return;
                }

                // 根據正確的調用方式：
                // List<Dictionary<string, List<List<object>>>> lsForward = CorpEmployeeService.loadForward(out lsDuty, null);
                var loadForwardMethod = corpEmployeeServiceType.GetMethod("loadForward", new Type[] { typeof(List<string>).MakeByRefType(), typeof(string) });

                if (loadForwardMethod == null)
                {
                    OutputError("找不到 loadForward 方法");
                    return;
                }

                // 準備參數 - lsDuty 是 out 參數，會由方法填充；table_name 傳入 null
                List<string> lsDuty = new List<string>();
                object[] methodArgs = new object[] { lsDuty, null };
                var result = loadForwardMethod.Invoke(null, methodArgs); // 靜態方法，第一個參數為 null

                // 取得 out 參數的值（雖然我們不需要用到）
                var updatedLsDuty = (List<string>)methodArgs[0];

                // 輸出 JSON 結果
                string jsonOutput = JsonConvert.SerializeObject(result, Formatting.Indented);
                Console.OutputEncoding = System.Text.Encoding.UTF8;
                Console.WriteLine(jsonOutput);
            }
            catch (Exception ex)
            {
                OutputError("執行失敗: " + ex.Message + "\n詳細錯誤: " + ex.ToString());
            }
        }

        static void OutputError(string message)
        {
            var errorResult = new
            {
                error = true,
                message = message
            };

            string jsonOutput = JsonConvert.SerializeObject(errorResult, Formatting.Indented);

            Console.WriteLine(jsonOutput);
        }
    }
}
