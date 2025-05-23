//+------------------------------------------------------------------+
//|                                                 SignalWriter.mq4 |
//|                                   SoloTrend X Signal Writer EA   |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "SoloTrend X"
#property link      "https://solotrendx.com"
#property version   "1.00"
#property strict

// External parameters
extern string SignalFile = "C:\\MT4_Dynamic_Trailing\\signals\\ea_signals.txt";
extern double DefaultVolume = 0.1;
extern int MagicNumber = 12345;
extern bool EnableSignals = true;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("SignalWriter EA initialized");
   Print("Signal file path: ", SignalFile);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("SignalWriter EA deinitialized");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   if(!EnableSignals) return;
   
   // Example: Simple MA crossover signal
   double fastMA = iMA(Symbol(), 0, 8, 0, MODE_SMA, PRICE_CLOSE, 0);
   double slowMA = iMA(Symbol(), 0, 21, 0, MODE_SMA, PRICE_CLOSE, 0);
   double prevFastMA = iMA(Symbol(), 0, 8, 0, MODE_SMA, PRICE_CLOSE, 1);
   double prevSlowMA = iMA(Symbol(), 0, 21, 0, MODE_SMA, PRICE_CLOSE, 1);
   
   // Check for buy signal
   if(prevFastMA <= prevSlowMA && fastMA > slowMA)
   {
      WriteSignal("buy", Symbol(), DefaultVolume, 0, 0, "MA Cross Buy", MagicNumber);
   }
   
   // Check for sell signal
   if(prevFastMA >= prevSlowMA && fastMA < slowMA)
   {
      WriteSignal("sell", Symbol(), DefaultVolume, 0, 0, "MA Cross Sell", MagicNumber);
   }
}

//+------------------------------------------------------------------+
//| Write signal to file in JSON format                             |
//+------------------------------------------------------------------+
void WriteSignal(string type, string symbol, double volume, 
                double sl = 0, double tp = 0, 
                string comment = "", int magic = 0, double price = 0, 
                int ticket = 0)
{
   // Create a unique signal ID
   string signal_id = IntegerToString(TimeCurrent()) + "_" + 
                     IntegerToString(GetTickCount()) + "_" + 
                     symbol;
   
   // Build JSON object
   string json = "[{";
   json += "\"signal_id\":\"" + signal_id + "\",";
   json += "\"type\":\"" + type + "\",";
   json += "\"symbol\":\"" + symbol + "\",";
   json += "\"login\":" + IntegerToString(AccountNumber()) + ",";
   json += "\"volume\":" + DoubleToString(volume, 2);
   
   // Add optional fields if provided
   if(sl > 0) json += ",\"sl\":" + DoubleToString(sl, Digits);
   if(tp > 0) json += ",\"tp\":" + DoubleToString(tp, Digits);
   if(comment != "") json += ",\"comment\":\"" + comment + "\"";
   if(magic > 0) json += ",\"magic\":" + IntegerToString(magic);
   if(price > 0) json += ",\"price\":" + DoubleToString(price, Digits);
   if(ticket > 0) json += ",\"ticket\":" + IntegerToString(ticket);
   
   json += "}]";
   
   // Write to file
   int handle = FileOpen(SignalFile, FILE_WRITE|FILE_TXT);
   if(handle != INVALID_HANDLE)
   {
      FileWriteString(handle, json);
      FileClose(handle);
      Print("Signal written to file: ", json);
   }
   else
   {
      Print("ERROR: Could not open signal file: ", SignalFile);
      Print("Error code: ", GetLastError());
   }
}

//+------------------------------------------------------------------+
//| Test function to manually write a signal                         |
//+------------------------------------------------------------------+
void TestSignal()
{
   WriteSignal("buy", Symbol(), 0.1, 0, 0, "Test Signal", MagicNumber);
}