using System;
using System.Data.OracleClient;
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

                // 連線字串
                string connString = "Data Source=sohya;User Id=topco;Password=erp;";

                using (OracleConnection conn = new OracleConnection(connString))
                {
                    conn.Open();

                    // 執行更新
                    string updateSql = @"
                        UPDATE wfinbox
                        SET xstatus = '3', xtime = sysdate
                        WHERE source = '003'
                        AND doc_type = '999'
                        AND empno = :empno
                        AND serino = :serino";

                    using (OracleCommand updateCmd = new OracleCommand(updateSql, conn))
                    {
                        updateCmd.Parameters.Add(new OracleParameter("empno", empno));
                        updateCmd.Parameters.Add(new OracleParameter("serino", serino));

                        int rowsAffected = updateCmd.ExecuteNonQuery();

                        if (rowsAffected > 0)
                        {
                            var successResult = new
                            {
                                success = true,
                                rowsAffected = rowsAffected,
                                empno = empno,
                                serino = serino,
                                message = "Wfinbox status updated to '3'"
                            };

                            string jsonOutput = JsonConvert.SerializeObject(successResult, Formatting.Indented);
                            Console.WriteLine(jsonOutput);
                        }
                        else
                        {
                            OutputError(string.Format("找不到符合條件的資料 (source='003', doc_type='999', empno='{0}', serino='{1}')", empno, serino));
                        }
                    }
                }
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
