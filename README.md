# EastAgileTracker

An open source software development planning and tracking for eXtreme Programming (XP) and agile development.

With the demise of Pivotal Tracker former customers need to extract their past and current projects and have a place to put that data. 

This project attempts to provide 
(1) migration tools from Pivotal Tracker: getting data out, helping get data into other tools like Linear, Jira, or Plane. 
(2) But also allowing extracted data to be staged outside of a SaaS in a database. Storing legacy projects outside of a SaaS can reduce costs, maintain security, but also needs to enable queries on the data when necessary.
(3) And this code can form the basis for creating entirely new applications for internal or commercial purposes (and, yes, Eastagile.com can help you build those).

What we have so far:

1.  A complete data model of the core parts of an eXtreme Programming oriented project planner (like Pivotal Tracker). This is available in Postgresql-ready DDL.
- Entity relationship diagram.
- DDL to implement the data model.
- The beginning of a AI conversation to write code to implement an project planning application on top of this data model.

![Entity-Relationship Diagram of Database Layer](./EastAgileTracke ER Diagram 2024-10-18 at 3.20.05 PM)


  



