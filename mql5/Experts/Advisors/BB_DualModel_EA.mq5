//+------------------------------------------------------------------+
//|                                            BB_DualModel_EA.mq5    |
//|        Pure Bollinger Bands EA - Mean Reversion OR Breakout      |
//|                                                                  |
//|  Live/Strategy-Tester port of the Python research engine in      |
//|  bb_research/. ONE expert, TWO selectable models. It mirrors the  |
//|  exact rules the backtester enforces so live behaviour matches    |
//|  the research:                                                    |
//|                                                                   |
//|    * NO LOOK-AHEAD: a signal is read from the just-CLOSED bar     |
//|      (shift 1) and the trade is entered on the OPEN of the new    |
//|      bar (shift 0). We never act on the still-forming bar's data. |
//|    * RISK MODEL: 1R = |entry_open - middle_band[closed_bar]|.     |
//|      BUY:  SL = entry - 1R,  TP = entry + RR*1R                    |
//|      SELL: SL = entry + 1R,  TP = entry - RR*1R                    |
//|    * ONE POSITION AT A TIME per (symbol, magic).                  |
//|                                                                   |
//|  Same-candle TP/SL: in the live market the broker resolves this;  |
//|  to reproduce the engine's CONSERVATIVE "SL first" assumption in  |
//|  the Strategy Tester, run with "Every tick based on real ticks".  |
//+------------------------------------------------------------------+
#property copyright "Trading research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

//--- Model selector ------------------------------------------------//
enum ENUM_BB_MODE
  {
   BB_MEAN_REVERSION = 0, // Mean Reversion (fade the bands)
   BB_BREAKOUT       = 1  // Breakout (follow the bands)
  };

//--- Lot sizing mode ----------------------------------------------//
enum ENUM_LOT_MODE
  {
   LOT_FIXED        = 0, // Fixed lot size
   LOT_RISK_PERCENT = 1  // Size from % balance risked over the SL distance
  };

//--- Inputs --------------------------------------------------------//
input group "Strategy"
input ENUM_BB_MODE InpMode        = BB_MEAN_REVERSION; // Model
input int          InpBBPeriod    = 20;                // BB period
input double       InpBBDeviation = 2.0;               // BB deviation
input double       InpRR          = 2.0;               // Reward : Risk (TP multiple of 1R)

input group "Money management"
input ENUM_LOT_MODE InpLotMode    = LOT_FIXED;         // Lot sizing mode
input double       InpFixedLots   = 0.10;              // Fixed lots (LOT_FIXED)
input double       InpRiskPercent = 1.0;               // Risk % of balance (LOT_RISK_PERCENT)

input group "Execution / filters"
input long         InpMagic       = 990201;            // Magic number
input int          InpMaxSpreadPts= 0;                 // Max spread in points (0 = no filter)
input int          InpSlippagePts = 20;                // Max deviation/slippage (points)

//--- Globals -------------------------------------------------------//
CTrade        g_trade;
int           g_bb_handle = INVALID_HANDLE;
datetime      g_last_bar_time = 0;

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpBBPeriod <= 1)
     {
      Print("ERROR: InpBBPeriod must be > 1");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(InpBBDeviation <= 0.0)
     {
      Print("ERROR: InpBBDeviation must be > 0");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(InpRR <= 0.0)
     {
      Print("ERROR: InpRR must be > 0");
      return(INIT_PARAMETERS_INCORRECT);
     }

   // shift = 0, applied price = close, to match the research engine.
   g_bb_handle = iBands(_Symbol, _Period, InpBBPeriod, 0, InpBBDeviation, PRICE_CLOSE);
   if(g_bb_handle == INVALID_HANDLE)
     {
      Print("ERROR: failed to create iBands handle");
      return(INIT_FAILED);
     }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpSlippagePts);
   g_trade.SetTypeFillingBySymbol(_Symbol);

   g_last_bar_time = iTime(_Symbol, _Period, 0);
   PrintFormat("BB_DualModel_EA started | mode=%s period=%d dev=%.2f RR=%.2f",
               (InpMode == BB_MEAN_REVERSION ? "MEAN_REVERSION" : "BREAKOUT"),
               InpBBPeriod, InpBBDeviation, InpRR);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(g_bb_handle != INVALID_HANDLE)
      IndicatorRelease(g_bb_handle);
  }

//+------------------------------------------------------------------+
//| Is there an open position for this symbol+magic?                 |
//+------------------------------------------------------------------+
bool HasOpenPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return(true);
     }
   return(false);
  }

//+------------------------------------------------------------------+
//| Compute lot size from the SL distance (price units)              |
//+------------------------------------------------------------------+
double CalcLots(double sl_distance_price)
  {
   double vol_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vol_min  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vol_max  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);

   double lots;
   if(InpLotMode == LOT_FIXED)
     {
      lots = InpFixedLots;
     }
   else
     {
      double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
      double risk_money = balance * (InpRiskPercent / 100.0);

      double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      double tick_size  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      if(tick_size <= 0.0 || tick_value <= 0.0 || sl_distance_price <= 0.0)
         return(0.0);

      // Loss for 1.0 lot if SL is hit = (distance / tick_size) * tick_value.
      double loss_per_lot = (sl_distance_price / tick_size) * tick_value;
      if(loss_per_lot <= 0.0)
         return(0.0);
      lots = risk_money / loss_per_lot;
     }

   // Normalise to the broker's volume step and clamp to [min, max].
   if(vol_step > 0.0)
      lots = MathFloor(lots / vol_step) * vol_step;
   lots = MathMax(vol_min, MathMin(vol_max, lots));
   return(lots);
  }

//+------------------------------------------------------------------+
//| New-bar handler: read closed bar, enter on the new bar's open    |
//+------------------------------------------------------------------+
void OnTick()
  {
   // Act only when a brand-new bar has opened. Index 1 is now the bar that
   // just CLOSED (the signal bar t); index 0 is the new bar we enter on.
   datetime cur_bar_time = iTime(_Symbol, _Period, 0);
   if(cur_bar_time == g_last_bar_time)
      return;
   g_last_bar_time = cur_bar_time;

   // One position at a time.
   if(HasOpenPosition())
      return;

   // Spread filter (optional).
   if(InpMaxSpreadPts > 0)
     {
      long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
      if(spread > InpMaxSpreadPts)
         return;
     }

   // --- Pull Bollinger Band values for the just-closed bar (shift 1) ----- //
   double mid[1], up[1], lo[1];
   if(CopyBuffer(g_bb_handle, 0, 1, 1, mid) != 1 ||
      CopyBuffer(g_bb_handle, 1, 1, 1, up)  != 1 ||
      CopyBuffer(g_bb_handle, 2, 1, 1, lo)  != 1)
      return; // bands not ready yet (warm-up)

   double middle_band = mid[0];
   double upper_band  = up[0];
   double lower_band  = lo[0];
   double close_t     = iClose(_Symbol, _Period, 1);
   if(close_t == 0.0 || middle_band == 0.0)
      return;

   // --- Signal logic (mirrors src/signals.py) ---------------------------- //
   bool want_buy  = false;
   bool want_sell = false;
   if(InpMode == BB_MEAN_REVERSION)
     {
      if(close_t < lower_band) want_buy  = true; // stretched below -> revert up
      if(close_t > upper_band) want_sell = true; // stretched above -> revert down
     }
   else // BB_BREAKOUT
     {
      if(close_t > upper_band) want_buy  = true; // breaking up   -> continue up
      if(close_t < lower_band) want_sell = true; // breaking down -> continue down
     }

   if(!want_buy && !want_sell)
      return;

   // --- Entry reference = OPEN of the new bar (shift 0) ------------------- //
   double entry_ref = iOpen(_Symbol, _Period, 0);
   double dist = MathAbs(entry_ref - middle_band); // 1R in price terms
   if(dist <= 0.0)
     {
      Print("Skip: invalid risk distance (entry == middle band)");
      return;
     }

   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double sl_price, tp_price;
   if(want_buy)
     {
      sl_price = NormalizeDouble(entry_ref - dist,          digits);
      tp_price = NormalizeDouble(entry_ref + InpRR * dist,  digits);
     }
   else
     {
      sl_price = NormalizeDouble(entry_ref + dist,          digits);
      tp_price = NormalizeDouble(entry_ref - InpRR * dist,  digits);
     }

   double lots = CalcLots(dist);
   if(lots <= 0.0)
     {
      Print("Skip: computed lot size is 0 (check risk inputs / SL distance)");
      return;
     }

   // --- Respect the broker's minimum stop distance ----------------------- //
   long   stops_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double point       = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double min_stop    = stops_level * point;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   bool ok;
   if(want_buy)
     {
      if(min_stop > 0.0 &&
         (ask - sl_price < min_stop || tp_price - ask < min_stop))
        {
         Print("Skip BUY: SL/TP closer than broker stops level");
         return;
        }
      ok = g_trade.Buy(lots, _Symbol, 0.0, sl_price, tp_price, "BB_DualModel BUY");
     }
   else
     {
      if(min_stop > 0.0 &&
         (sl_price - bid < min_stop || bid - tp_price < min_stop))
        {
         Print("Skip SELL: SL/TP closer than broker stops level");
         return;
        }
      ok = g_trade.Sell(lots, _Symbol, 0.0, sl_price, tp_price, "BB_DualModel SELL");
     }

   if(!ok)
      PrintFormat("Order failed: retcode=%d %s",
                  g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
   else
      PrintFormat("%s %.2f lots | entry_ref=%.*f SL=%.*f TP=%.*f (1R=%.*f, RR=%.2f)",
                  (want_buy ? "BUY" : "SELL"), lots,
                  digits, entry_ref, digits, sl_price, digits, tp_price,
                  digits, dist, InpRR);
  }
//+------------------------------------------------------------------+
