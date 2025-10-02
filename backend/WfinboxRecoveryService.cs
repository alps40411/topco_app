using System;
using System.Reflection;
using Newtonsoft.Json;

namespace WfinboxRecoveryService
{
    class Program
    {
        static void Main(string[] args)
        {
            try
            {
                // 設定控制台編碼為 UTF-8
                Console.OutputEncoding = System.Text.Encoding.UTF8;

                // 檢查參數
                if (args.Length < 2)
                {
                    OutputError("缺少必要參數: empno 和 serino");
                    return;
                }

                string empno = args[0];
                string serino = args[1];

                // 調用 MyReport.dll 中的 DailyReportService.WfinboxRecovery
                var myReportAssembly = Assembly.LoadFrom("MyReport.dll");
                var dailyReportServiceType = myReportAssembly.GetType("MyReport.Services.DailyReportService");

                if (dailyReportServiceType == null)
                {
                    OutputError("找不到 MyReport.Services.DailyReportService 類別");
                    return;
                }

                // 尋找 WfinboxRecovery 方法
                var wfinboxRecoveryMethod = dailyReportServiceType.GetMethod("WfinboxRecovery");

                if (wfinboxRecoveryMethod == null)
                {
                    OutputError("找不到 WfinboxRecovery 方法");
                    return;
                }

                // WfinboxRecovery 方法簽名: void WfinboxRecovery(Decimal serino, String empNo)
                // 注意：參數順序是 serino 在前，empNo 在後
                decimal serinoDecimal = decimal.Parse(serino);
                object[] methodArgs = new object[] { serinoDecimal, empno };

                // 創建 DailyReportService 實例並調用方法
                var instance = Activator.CreateInstance(dailyReportServiceType);
                object result = wfinboxRecoveryMethod.Invoke(instance, methodArgs);

                // 輸出成功結果
                var successResult = new
                {
                    success = true,
                    empno = empno,
                    serino = serino,
                    message = "Wfinbox status updated successfully via MyReport.dll",
                    result = result
                };

                string jsonOutput = JsonConvert.SerializeObject(successResult, Formatting.Indented);
                Console.WriteLine(jsonOutput);
            }
            catch (TargetInvocationException tie)
            {
                // 展開內部異常
                var innerEx = tie.InnerException ?? tie;
                OutputError("調用 MyReport.dll 失敗: " + innerEx.Message + "\n詳細錯誤: " + innerEx.ToString());
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
