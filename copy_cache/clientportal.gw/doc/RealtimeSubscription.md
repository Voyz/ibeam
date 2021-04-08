# Streaming Websocket Data
The websocket end-point is available at **wss://gateway-ip:port/v1/portal/ws**

Once the websocket connection is established, you can send subscription requests in the following format: 
> s+TOPIC+ARGUMENTS

Where s and + characters are their literal forms: 's' for subscription and '+' is used as separator. Currently supported topics are: 
 - realtime-account-data
 - md

*realtime-data* is additionally planned for release soon. There is a test page available at: [https://interactivebrokers.github.io/cpwebapi/RealtimeSubscription.html](https://interactivebrokers.github.io/cpwebapi/RealtimeSubscription.html). Every response message will contain the topic associated with the original request.

#### Order and P&L Data


The *realtime-account-data* subscription provides updates for Orders and P&L information for the given account and requires an account number as argument:

> s+realtime-account-data+UXXXX

When subscribed, the backend will push order updates and PnL information. Order updates will include all filled/cancelled/working orders for the current day and will look like the following:
> {"orders":[{"acct":"UXXXX", "conid": 1234, ....}, ...], "topic": "realtime-account-data+UXXXX"}

Where *orders* is an Array of Json Objects containing various information about the orders. 
#### Market Data
The *md* subscription is used to subscribe to Market Data for a given conId. Conids (Contract IDs) are internal to IBKR and uniquely define a financial instrument in the IBKR database. The **/secdef** end-point can be used to do security identifier to conid lookup for stocks, **/trsrv/futures** can be used for futures, and for options there is an additional step described [here](https://interactivebrokers.github.io/cpwebapi/option_lookup.html). Before requesting streaming websocket data, the endpoint **/iserver/accounts** must be called. 

The portfolio positions end-point returns a conid for each position with the security definition, like name or ticker.
   
The *md* subscription also accepts special options that affect the subscription and can be passed as JSON Object. Those options are:

  
- **tempo**: A number in milliseconds. This number affects the tick update frequency. Without tempo set, the backend will push all tick updates to the client. If tempo is set to 5000 (5 seconds), the backend will keep an internal map of key, values to store all tick updates, only after the 5 seconds and will push the map to the client those 5 seconds have elapsed.
- **snapshot**: Boolean, true or false. When true, the backend will send a snapshot of all information currently available for the conid.
- **fields**: A comma separated list of fields as described in the /marketdata/snapshot end-point.

A sample request:
> s+md+107113386+{"tempo":1000,"snapshot":true,"fields":"55,22,23"}

 A sample response:


> {"31":154.81, "topic":"md+107113386"}


The "md" subscription also supports unsubscribing to the topic with *u+md+CONID*, e.g.

> u+md+107113386

