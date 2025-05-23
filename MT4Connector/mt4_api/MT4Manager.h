//+------------------------------------------------------------------+
//|                                 MT4 Manager API C++ Wrapper Class |
//+------------------------------------------------------------------+
#ifndef MT4MANAGER_H
#define MT4MANAGER_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <vector>
#include <string>
#include <time.h>
#include <windows.h>
#include <winsock2.h>
#include "../MT4ManagerAPI/MT4ManagerAPI.h"

// Forward declarations for C++ classes
class MT4Manager;
class MT4Account;
class MT4Symbol;
class MT4Trade;

//+------------------------------------------------------------------+
//| MT4Account - Wrapper for user accounts                           |
//+------------------------------------------------------------------+
class MT4Account {
private:
    UserRecord user;
    friend class MT4Manager;

public:
    MT4Account(const UserRecord& user_record) : user(user_record) {}
    
    // Getters
    int getLogin() const { return user.login; }
    const char* getGroup() const { return user.group; }
    const char* getName() const { return user.name; }
    const char* getEmail() const { return user.email; }
    double getBalance() const { return user.balance; }
    double getCredit() const { return user.credit; }
    time_t getRegistrationDate() const { return user.regdate; }
    time_t getLastLoginDate() const { return user.lastdate; }
    int getLeverage() const { return user.leverage; }
    
    // Print account information
    void print() const {
        printf("Account #%d\n", user.login);
        printf("  Name   : %s\n", user.name);
        printf("  Group  : %s\n", user.group);
        printf("  Email  : %s\n", user.email);
        printf("  Balance: %.2f\n", user.balance);
        printf("  Credit : %.2f\n", user.credit);
        
        char time_buf[64];
        time_t reg_time = user.regdate;
        strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", localtime(&reg_time));
        printf("  Registered: %s\n", time_buf);
        
        time_t last_time = user.lastdate;
        strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", localtime(&last_time));
        printf("  Last login: %s\n", time_buf);
    }
};

//+------------------------------------------------------------------+
//| MT4Symbol - Wrapper for symbol information                       |
//+------------------------------------------------------------------+
class MT4Symbol {
private:
    ConSymbol symbol;
    SymbolInfo info;
    bool has_info;
    friend class MT4Manager;

public:
    MT4Symbol(const ConSymbol& symbol_data) 
        : symbol(symbol_data), has_info(false) {}
    
    MT4Symbol(const ConSymbol& symbol_data, const SymbolInfo& symbol_info) 
        : symbol(symbol_data), info(symbol_info), has_info(true) {}
    
    // Getters
    const char* getName() const { return symbol.symbol; }
    const char* getDescription() const { return symbol.description; }
    const char* getCurrency() const { return symbol.currency; }
    int getDigits() const { return symbol.digits; }
    double getPoint() const { return symbol.point; }
    int getSpread() const { return symbol.spread; }
    double getContractSize() const { return symbol.contract_size; }
    double getTickValue() const { return symbol.tick_value; }
    double getTickSize() const { return symbol.tick_size; }
    
    // Current price information (if available)
    bool hasCurrentInfo() const { return has_info; }
    double getBid() const { return has_info ? info.bid : 0.0; }
    double getAsk() const { return has_info ? info.ask : 0.0; }
    time_t getLastTime() const { return has_info ? info.lasttime : 0; }
    
    // Print symbol information
    void print() const {
        printf("Symbol: %s (%s)\n", symbol.symbol, symbol.description);
        printf("  Currency    : %s\n", symbol.currency);
        printf("  Digits      : %d\n", symbol.digits);
        printf("  Point       : %.8f\n", symbol.point);
        printf("  Spread      : %d\n", symbol.spread);
        printf("  Contract Size: %.2f\n", symbol.contract_size);
        printf("  Tick Value  : %.5f\n", symbol.tick_value);
        printf("  Tick Size   : %.8f\n", symbol.tick_size);
        
        if (has_info) {
            printf("  Current Bid : %.5f\n", info.bid);
            printf("  Current Ask : %.5f\n", info.ask);
            
            char time_buf[64];
            time_t last_time = info.lasttime;
            strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", localtime(&last_time));
            printf("  Last Update : %s\n", time_buf);
        }
    }
};

//+------------------------------------------------------------------+
//| MT4Trade - Wrapper for trade records                             |
//+------------------------------------------------------------------+
class MT4Trade {
private:
    TradeRecord trade;
    friend class MT4Manager;

public:
    MT4Trade(const TradeRecord& trade_record) : trade(trade_record) {}
    
    // Getters
    int getTicket() const { return trade.order; }
    int getLogin() const { return trade.login; }
    const char* getSymbol() const { return trade.symbol; }
    int getType() const { return trade.cmd; }
    int getVolume() const { return trade.volume; }
    double getOpenPrice() const { return trade.open_price; }
    double getClosePrice() const { return trade.close_price; }
    double getStopLoss() const { return trade.sl; }
    double getTakeProfit() const { return trade.tp; }
    time_t getOpenTime() const { return trade.open_time; }
    time_t getCloseTime() const { return trade.close_time; }
    double getProfit() const { return trade.profit; }
    double getCommission() const { return trade.commission; }
    double getSwap() const { return trade.storage; }
    const char* getComment() const { return trade.comment; }
    
    // Check if trade is open
    bool isOpen() const { return trade.close_time == 0; }
    
    // Get trade type as string
    std::string getTypeAsString() const {
        switch (trade.cmd) {
            case OP_BUY: return "Buy";
            case OP_SELL: return "Sell";
            case OP_BUY_LIMIT: return "Buy Limit";
            case OP_SELL_LIMIT: return "Sell Limit";
            case OP_BUY_STOP: return "Buy Stop";
            case OP_SELL_STOP: return "Sell Stop";
            case OP_BALANCE: return "Balance";
            case OP_CREDIT: return "Credit";
            default: return "Unknown";
        }
    }
    
    // Print trade information
    void print() const {
        printf("Order #%d (%s)\n", trade.order, getTypeAsString().c_str());
        printf("  Login  : %d\n", trade.login);
        printf("  Symbol : %s\n", trade.symbol);
        printf("  Volume : %d\n", trade.volume);
        printf("  Open   : %.5f\n", trade.open_price);
        
        char time_buf[64];
        time_t open_time = trade.open_time;
        strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", localtime(&open_time));
        printf("  Opened : %s\n", time_buf);
        
        if (trade.close_time > 0) {
            printf("  Close  : %.5f\n", trade.close_price);
            
            time_t close_time = trade.close_time;
            strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", localtime(&close_time));
            printf("  Closed : %s\n", time_buf);
        } else {
            printf("  SL     : %.5f\n", trade.sl);
            printf("  TP     : %.5f\n", trade.tp);
        }
        
        printf("  Profit : %.2f\n", trade.profit);
        printf("  Comm.  : %.2f\n", trade.commission);
        printf("  Swap   : %.2f\n", trade.storage);
        printf("  Comment: %s\n", trade.comment);
    }
};

//+------------------------------------------------------------------+
//| MT4Manager - Main wrapper class for MT4 Manager API              |
//+------------------------------------------------------------------+
class MT4Manager {
private:
    CManagerFactory m_factory;
    CManagerInterface* m_manager;
    bool m_connected;
    bool m_logged_in;
    std::string m_server;
    int m_login;
    std::string m_last_error;
    
    void setLastError(int code) {
        if (m_manager != NULL) {
            m_last_error = m_manager->ErrorDescription(code);
        } else {
            m_last_error = "Manager interface not initialized";
        }
    }

public:
    MT4Manager() : m_factory(), m_manager(NULL), m_connected(false), m_logged_in(false), m_login(0) {
        m_factory.WinsockStartup();
        if (m_factory.IsValid()) {
            m_manager = m_factory.Create(ManAPIVersion);
        }
    }
    
    ~MT4Manager() {
        if (m_manager != NULL) {
            if (m_connected) {
                m_manager->Disconnect();
            }
            m_manager->Release();
            m_manager = NULL;
        }
        m_factory.WinsockCleanup();
    }
    
    // Check if manager interface is valid
    bool isValid() const {
        return m_manager != NULL;
    }
    
    // Get last error message
    const char* getLastError() const {
        return m_last_error.c_str();
    }
    
    // Connect to MT4 server
    bool connect(const char* server) {
        if (!isValid()) {
            m_last_error = "Manager interface not initialized";
            return false;
        }
        
        int res = m_manager->Connect(server);
        if (res != RET_OK) {
            setLastError(res);
            return false;
        }
        
        m_connected = true;
        m_server = server;
        return true;
    }
    
    // Login to MT4 server
    bool login(int login, const char* password) {
        if (!isValid() || !m_connected) {
            m_last_error = "Not connected to server";
            return false;
        }
        
        int res = m_manager->Login(login, password);
        if (res != RET_OK) {
            setLastError(res);
            return false;
        }
        
        m_logged_in = true;
        m_login = login;
        return true;
    }
    
    // Disconnect from MT4 server
    void disconnect() {
        if (isValid() && m_connected) {
            m_manager->Disconnect();
            m_connected = false;
            m_logged_in = false;
        }
    }
    
    // Check if connected to MT4 server
    bool isConnected() const {
        return m_connected && (m_manager ? m_manager->IsConnected() : false);
    }
    
    // Check if logged in to MT4 server
    bool isLoggedIn() const {
        return m_logged_in;
    }
    
    // Get server time
    time_t getServerTime() {
        if (!isValid() || !m_logged_in) {
            return 0;
        }
        
        return m_manager->ServerTime();
    }
    
    // Get all user accounts
    std::vector<MT4Account> getAccounts() {
        std::vector<MT4Account> accounts;
        
        if (!isValid() || !m_logged_in) {
            return accounts;
        }
        
        int total = 0;
        UserRecord* users = m_manager->UsersRequest(&total);
        
        if (users && total > 0) {
            for (int i = 0; i < total; i++) {
                accounts.push_back(MT4Account(users[i]));
            }
            
            m_manager->MemFree(users);
        }
        
        return accounts;
    }
    
    // Get account by login
    MT4Account* getAccount(int login) {
        if (!isValid() || !m_logged_in) {
            return NULL;
        }
        
        UserRecord user;
        int res = m_manager->UserRecordGet(login, &user);
        
        if (res != RET_OK) {
            setLastError(res);
            return NULL;
        }
        
        return new MT4Account(user);
    }
    
    // Get all symbols
    std::vector<MT4Symbol> getSymbols() {
        std::vector<MT4Symbol> symbols;
        
        if (!isValid() || !m_logged_in) {
            return symbols;
        }
        
        int total = 0;
        ConSymbol* syms = m_manager->SymbolsGetAll(&total);
        
        if (syms && total > 0) {
            for (int i = 0; i < total; i++) {
                symbols.push_back(MT4Symbol(syms[i]));
            }
            
            m_manager->MemFree(syms);
        }
        
        return symbols;
    }
    
    // Get symbol by name
    MT4Symbol* getSymbol(const char* symbol_name) {
        if (!isValid() || !m_logged_in) {
            return NULL;
        }
        
        ConSymbol cs;
        int res = m_manager->SymbolGet(symbol_name, &cs);
        
        if (res != RET_OK) {
            setLastError(res);
            return NULL;
        }
        
        SymbolInfo si;
        res = m_manager->SymbolInfoGet(symbol_name, &si);
        
        if (res == RET_OK) {
            return new MT4Symbol(cs, si);
        } else {
            return new MT4Symbol(cs);
        }
    }
    
    // Get all trades
    std::vector<MT4Trade> getTrades() {
        std::vector<MT4Trade> trades;
        
        if (!isValid() || !m_logged_in) {
            return trades;
        }
        
        int total = 0;
        TradeRecord* tr = m_manager->TradesRequest(&total);
        
        if (tr && total > 0) {
            for (int i = 0; i < total; i++) {
                trades.push_back(MT4Trade(tr[i]));
            }
            
            m_manager->MemFree(tr);
        }
        
        return trades;
    }
    
    // Get trades by login
    std::vector<MT4Trade> getTradesByLogin(int login) {
        std::vector<MT4Trade> trades;
        
        if (!isValid() || !m_logged_in) {
            return trades;
        }
        
        int total = 0;
        TradeRecord* tr = m_manager->TradesGetByLogin(login, NULL, &total);
        
        if (tr && total > 0) {
            for (int i = 0; i < total; i++) {
                trades.push_back(MT4Trade(tr[i]));
            }
            
            m_manager->MemFree(tr);
        }
        
        return trades;
    }
    
    // Get trades by symbol
    std::vector<MT4Trade> getTradesBySymbol(const char* symbol) {
        std::vector<MT4Trade> trades;
        
        if (!isValid() || !m_logged_in) {
            return trades;
        }
        
        int total = 0;
        TradeRecord* tr = m_manager->TradesGetBySymbol(symbol, &total);
        
        if (tr && total > 0) {
            for (int i = 0; i < total; i++) {
                trades.push_back(MT4Trade(tr[i]));
            }
            
            m_manager->MemFree(tr);
        }
        
        return trades;
    }
    
    // Get trade by ticket
    MT4Trade* getTradeByTicket(int ticket) {
        if (!isValid() || !m_logged_in) {
            return NULL;
        }
        
        TradeRecord trade;
        int res = m_manager->TradeRecordGet(ticket, &trade);
        
        if (res != RET_OK) {
            setLastError(res);
            return NULL;
        }
        
        return new MT4Trade(trade);
    }
    
    // Open a trade
    int openTrade(int login, const char* symbol, int cmd, double volume, 
                double price, double sl = 0, double tp = 0, const char* comment = "") {
        if (!isValid() || !m_logged_in) {
            m_last_error = "Not connected or not logged in";
            return 0;
        }
        
        TradeTransInfo trade = {0};
        trade.type = TT_BR_ORDER_OPEN;
        trade.cmd = cmd;
        trade.orderby = login;
        strncpy(trade.symbol, symbol, sizeof(trade.symbol) - 1);
        trade.volume = (int)(volume * 100); // Convert from lots to lot size
        trade.price = price;
        trade.sl = sl;
        trade.tp = tp;
        
        if (comment && *comment) {
            strncpy(trade.comment, comment, sizeof(trade.comment) - 1);
        }
        
        int res = m_manager->TradeTransaction(&trade);
        if (res != RET_OK) {
            setLastError(res);
            return 0;
        }
        
        // Find the new order
        int total = 0;
        TradeRecord* trades = m_manager->TradesGetByLogin(login, NULL, &total);
        int order_ticket = 0;
        
        if (trades && total > 0) {
            // Find the most recent trade
            time_t newest_time = 0;
            
            for (int i = 0; i < total; i++) {
                if (trades[i].open_time > newest_time) {
                    newest_time = trades[i].open_time;
                    order_ticket = trades[i].order;
                }
            }
            
            m_manager->MemFree(trades);
        }
        
        return order_ticket;
    }
    
    // Close a trade
    bool closeTrade(int ticket, double price = 0) {
        if (!isValid() || !m_logged_in) {
            m_last_error = "Not connected or not logged in";
            return false;
        }
        
        TradeTransInfo trade = {0};
        trade.type = TT_BR_ORDER_CLOSE;
        trade.order = ticket;
        
        if (price > 0) {
            trade.price = price;
        }
        
        int res = m_manager->TradeTransaction(&trade);
        if (res != RET_OK) {
            setLastError(res);
            return false;
        }
        
        return true;
    }
    
    // Modify a trade
    bool modifyTrade(int ticket, double sl, double tp) {
        if (!isValid() || !m_logged_in) {
            m_last_error = "Not connected or not logged in";
            return false;
        }
        
        TradeTransInfo trade = {0};
        trade.type = TT_BR_ORDER_MODIFY;
        trade.order = ticket;
        trade.sl = sl;
        trade.tp = tp;
        
        int res = m_manager->TradeTransaction(&trade);
        if (res != RET_OK) {
            setLastError(res);
            return false;
        }
        
        return true;
    }
    
    // Get margin level for a login
    bool getMarginLevel(int login, double& balance, double& equity, 
                        double& margin, double& free_margin, double& margin_level) {
        if (!isValid() || !m_logged_in) {
            m_last_error = "Not connected or not logged in";
            return false;
        }
        
        MarginLevel ml;
        int res = m_manager->MarginLevelRequest(login, &ml);
        
        if (res != RET_OK) {
            setLastError(res);
            return false;
        }
        
        balance = ml.balance;
        equity = ml.equity;
        margin = ml.margin;
        free_margin = ml.margin_free;
        margin_level = ml.margin_level;
        
        return true;
    }
    
    // Get online users
    int getOnlineUsersCount() {
        if (!isValid() || !m_logged_in) {
            return 0;
        }
        
        int total = 0;
        OnlineRecord* online = m_manager->OnlineRequest(&total);
        
        if (online) {
            m_manager->MemFree(online);
        }
        
        return total;
    }
    
    // Check if user is online
    bool isUserOnline(int login) {
        if (!isValid() || !m_logged_in) {
            return false;
        }
        
        int total = 0;
        OnlineRecord* online = m_manager->OnlineRequest(&total);
        bool found = false;
        
        if (online && total > 0) {
            for (int i = 0; i < total; i++) {
                if (online[i].login == login) {
                    found = true;
                    break;
                }
            }
            
            m_manager->MemFree(online);
        }
        
        return found;
    }
    
    // Get direct access to the manager interface (for advanced operations)
    CManagerInterface* getManagerInterface() {
        return m_manager;
    }
};

#endif // MT4MANAGER_H