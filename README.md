Price Tracker
=============

A script that sends an email notification when a specified item's price changes. Currently, the following websites are
supported:

- www.emag.bg
- www.ozone.bg
- www.ardes.bg

The idea is to make it run automatically at a specific interval, e.g. with a Cron or Launchd job.

You should provide an `.env` file with:

- a Google sender email (`SENDER_EMAIL` variable)
- password (`EMAIL_PASSWORD` variable)

for the notifications.