//+------------------------------------------------------------------+
//|                                        DynamicTrailingStop.mq4   |
//|                                              SoloTrend X          |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "SoloTrend X"
#property link      ""
#property version   "1.00"
#property strict

// Input parameters
input double TP1 = 1.0;                    // Take Profit Level 1 (in price)
input double TP2 = 2.0;                    // Take Profit Level 2 (in price)
input double TP3 = 3.0;                    // Take Profit Level 3 (in price)
input int TrailingPips1 = 5;               // Trailing pips for Phase 1 (break-even + pips)
input int TrailingBuffer = 10;             // Buffer pips below TP2 for Phase 2
input double PercentageTrailing = 0.01;    // Percentage trailing for Phase 3 (1% = 0.01)
input int MagicNumber = 12345;             // Magic number for order identification (0 = all orders)
input bool EnableAlerts = true;            // Enable alerts when SL is modified

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Validate input parameters
   if(TP1 <= 0 || TP2 <= 0 || TP3 <= 0)
   {
      Alert("Invalid TP levels. All TP levels must be greater than 0.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   
   if(TP1 >= TP2 || TP2 >= TP3)
   {
      Alert("Invalid TP levels. TP1 < TP2 < TP3 required.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   
   if(TrailingPips1 < 0 || TrailingBuffer < 0)
   {
      Alert("Trailing pips and buffer must be non-negative.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   
   if(PercentageTrailing < 0 || PercentageTrailing > 1)
   {
      Alert("Percentage trailing must be between 0 and 1.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   
   Print("Dynamic Trailing Stop EA initialized successfully");
   Print("TP1: ", TP1, " TP2: ", TP2, " TP3: ", TP3);
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("Dynamic Trailing Stop EA deinitialized");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   UpdateDynamicTrailingStop();
}

//+------------------------------------------------------------------+
//| Update dynamic trailing stop for all orders                     |
//+------------------------------------------------------------------+
void UpdateDynamicTrailingStop()
{
   // Loop through all open orders
   for(int i = OrdersTotal()-1; i >= 0; i--)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         // Check if order is for current symbol
         if(OrderSymbol() != Symbol()) continue;
         
         // Check magic number if specified (0 means process all orders)
         if(MagicNumber != 0 && OrderMagicNumber() != MagicNumber) continue;
         
         // Process Buy orders
         if(OrderType() == OP_BUY)
         {
            ProcessBuyOrder();
         }
         // Process Sell orders
         else if(OrderType() == OP_SELL)
         {
            ProcessSellOrder();
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Process trailing stop for Buy orders                            |
//+------------------------------------------------------------------+
void ProcessBuyOrder()
{
   double currentPrice = Bid;
   double openPrice    = OrderOpenPrice();
   double currentSL    = OrderStopLoss();
   double newSL        = currentSL; // initialize with current SL
   string phase        = "";

   // Phase 1: When current price reaches TP1, move SL to break-even + TrailingPips1
   if(currentPrice >= TP1)
   {
      double phase1SL = openPrice + TrailingPips1 * Point;
      if(phase1SL > newSL)
      {
         newSL = phase1SL;
         phase = "Phase 1";
      }
   }
   
   // Phase 2: When current price reaches TP2, set SL just below TP2
   if(currentPrice >= TP2)
   {
      double phase2SL = TP2 - TrailingBuffer * Point;
      if(phase2SL > newSL)
      {
         newSL = phase2SL;
         phase = "Phase 2";
      }
   }
   
   // Phase 3: As price nears TP3 (within 5%), trail SL dynamically at a percentage below current price
   if(currentPrice >= TP3 * 0.95)
   {
      double phase3SL = currentPrice - (PercentageTrailing * currentPrice);
      if(phase3SL > newSL)
      {
         newSL = phase3SL;
         phase = "Phase 3";
      }
   }
   
   // Modify the order's SL if a higher (more protective) SL is found
   if(newSL > currentSL && newSL != currentSL)
   {
      // Normalize the stop loss to proper decimal places
      newSL = NormalizeDouble(newSL, Digits);
      
      if(OrderModify(OrderTicket(), openPrice, newSL, OrderTakeProfit(), 0, clrBlue))
      {
         Print("Buy Order #", OrderTicket(), " SL modified to ", newSL, " (", phase, ")");
         if(EnableAlerts)
            Alert("Buy Order #", OrderTicket(), " trailing stop updated (", phase, ")");
      }
      else
      {
         Print("Error modifying Buy Order #", OrderTicket(), ": ", GetLastError());
      }
   }
}

//+------------------------------------------------------------------+
//| Process trailing stop for Sell orders                           |
//+------------------------------------------------------------------+
void ProcessSellOrder()
{
   double currentPrice = Ask;
   double openPrice    = OrderOpenPrice();
   double currentSL    = OrderStopLoss();
   double newSL        = currentSL; // initialize with current SL
   string phase        = "";

   // For Sell orders, we need to invert the logic
   // Phase 1: When current price reaches TP1, move SL to break-even - TrailingPips1
   if(currentPrice <= TP1)
   {
      double phase1SL = openPrice - TrailingPips1 * Point;
      if(currentSL == 0 || phase1SL < newSL)
      {
         newSL = phase1SL;
         phase = "Phase 1";
      }
   }
   
   // Phase 2: When current price reaches TP2, set SL just above TP2
   if(currentPrice <= TP2)
   {
      double phase2SL = TP2 + TrailingBuffer * Point;
      if(currentSL == 0 || phase2SL < newSL)
      {
         newSL = phase2SL;
         phase = "Phase 2";
      }
   }
   
   // Phase 3: As price nears TP3 (within 5%), trail SL dynamically at a percentage above current price
   if(currentPrice <= TP3 * 1.05)
   {
      double phase3SL = currentPrice + (PercentageTrailing * currentPrice);
      if(currentSL == 0 || phase3SL < newSL)
      {
         newSL = phase3SL;
         phase = "Phase 3";
      }
   }
   
   // Modify the order's SL if a lower (more protective) SL is found for Sell orders
   if((currentSL == 0 || newSL < currentSL) && newSL != currentSL)
   {
      // Normalize the stop loss to proper decimal places
      newSL = NormalizeDouble(newSL, Digits);
      
      if(OrderModify(OrderTicket(), openPrice, newSL, OrderTakeProfit(), 0, clrRed))
      {
         Print("Sell Order #", OrderTicket(), " SL modified to ", newSL, " (", phase, ")");
         if(EnableAlerts)
            Alert("Sell Order #", OrderTicket(), " trailing stop updated (", phase, ")");
      }
      else
      {
         Print("Error modifying Sell Order #", OrderTicket(), ": ", GetLastError());
      }
   }
}