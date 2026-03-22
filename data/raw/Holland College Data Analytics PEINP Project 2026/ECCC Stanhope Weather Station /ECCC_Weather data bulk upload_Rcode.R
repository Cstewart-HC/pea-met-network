##################################################################
## R code for extracting multiples years of weather data on ECCC website ##
##################################################################

## Codes taken from:
## https://docs.ropensci.org/weathercan/

install.packages("weathercan", 
                 repos = c("https://ropensci.r-universe.dev", 
                           "https://cloud.r-project.org"))
library(weathercan)

## Code to see all available ECCC stations
head(stations())

## Specific search for unique station

stations_search("Stanhope", interval = "day")
stations_search("Stanhope", interval = "hour")

## PEI Stanhope station ID is 6545

Stanhope_daily_1961_1969 <- weather_dl(station_ids = 6545, start = "1961-01-01", end = "1969-12-31", interval = "day")
write.csv(Stanhope_daily_1961_1969,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_daily_1961-1969.csv")

Stanhope_daily_1970_1979 <- weather_dl(station_ids = 6545, start = "1970-01-01", end = "1979-12-31", interval = "day")
write.csv(Stanhope_daily_1970_1979,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_daily_1970-1979.csv")

Stanhope_daily_1980_1989 <- weather_dl(station_ids = 6545, start = "1980-01-01", end = "1989-12-31", interval = "day")
write.csv(Stanhope_daily_1980_1989,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_daily_1980-1989.csv")

Stanhope_daily_1990_1999 <- weather_dl(station_ids = 6545, start = "1990-01-01", end = "1999-12-31", interval = "day")
write.csv(Stanhope_daily_1990_1999,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_daily_1990-1999.csv")

Stanhope_daily_2000_2009 <- weather_dl(station_ids = 6545, start = "2000-01-01", end = "2009-12-31", interval = "day")
write.csv(Stanhope_daily_2000_2009,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_daily_2000-2009.csv")

Stanhope_daily_2010_2013 <- weather_dl(station_ids = 6545, start = "2010-01-01", end = "2013-12-31", interval = "day")
write.csv(Stanhope_daily_2010_2013,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_daily_2010-2013.csv")

Stanhope_hourly_2013 <- weather_dl(station_ids = 6545, start = "2013-01-01", end = "2013-12-31")
write.csv(Stanhope_hourly_2013,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_Hourly_2013.csv")

Stanhope_hourly_2014 <- weather_dl(station_ids = 6545, start = "2014-01-01", end = "2014-12-31")
write.csv(Stanhope_hourly_2014,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_Hourly_2014.csv")

Stanhope_hourly_2015 <- weather_dl(station_ids = 6545, start = "2015-01-01", end = "2015-12-31")
write.csv(Stanhope_hourly_2015,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_Hourly_2015.csv")

Stanhope_hourly_2016 <- weather_dl(station_ids = 6545, start = "2016-01-01", end = "2016-12-31")
write.csv(Stanhope_hourly_2016,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_Hourly_2016.csv")

Stanhope_hourly_2017 <- weather_dl(station_ids = 6545, start = "2017-01-01", end = "2017-12-31")
write.csv(Stanhope_hourly_2017,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_Hourly_2017.csv")

Stanhope_hourly_2018 <- weather_dl(station_ids = 6545, start = "2018-01-01", end = "2018-12-31")
write.csv(Stanhope_hourly_2018,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_Hourly_2018.csv")

Stanhope_hourly_2019 <- weather_dl(station_ids = 6545, start = "2019-01-01", end = "2019-12-31")
write.csv(Stanhope_hourly_2019,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_Hourly_2019.csv")

Stanhope_hourly_2020 <- weather_dl(station_ids = 6545, start = "2020-01-01", end = "2020-12-31")
write.csv(Stanhope_hourly_2020,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_Hourly_2020.csv")

Stanhope_hourly_2021 <- weather_dl(station_ids = 6545, start = "2021-01-01", end = "2021-12-31")
write.csv(Stanhope_hourly_2021,"X:/NEW Resource Conservation/6.4 Climate Change/Knowledge/Weather Stations + Tide Gauges/Data + Metadata/Raw data/Stanhope/Stanhope_Hourly_2021.csv")


