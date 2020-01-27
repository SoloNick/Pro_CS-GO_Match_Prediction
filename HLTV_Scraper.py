from bs4 import BeautifulSoup
from time import sleep
from datetime import datetime, timedelta
import pandas as pd
import urllib3
import re

class hltvScraper:
    """ Scrapes CS:GO stats from HLTV.org """

    def __init__(self):

        # self.soup = None
        self.domain = 'https://www.hltv.org'
        self.ranking_url = '/ranking/teams/'
        self.map_translate = {'Dust2': 'de_dust2',
                              'Nuke': 'de_nuke',
                              'Inferno': 'de_inferno',
                              'Vertigo': 'de_vertigo',
                              'Overpass': 'de_overpass',
                              'Train': 'de_train',
                              'Mirage': 'de_mirage'}
        self.basic_parse = {}


    def get_soup(self, link):
        """
        Read the soup from hltv webpage

        :param link: link to hltv pag. Ex: '/ranking/teams'
        :return: soup
        """
        url = self.domain + link
        link_soup = self.get_soup_helper(url)
        sleep(0.2)
        return link_soup


    def get_soup_helper(self, url):
        """
        Helper function for the get_soup function

        """
        if 'hltv' not in url.split('.'):
            raise Exception('Given url, {}, is not in the HLTV domain'.format(url))

        try:
            http = urllib3.PoolManager()
            response = http.request('GET', url)
            return BeautifulSoup(response.data, 'html.parser')

        except Exception as e:
            print(str(e))
            raise e


    def get_basic_parse(self):
        """
        Parses the top30 rankings for team name, id, rank, points, link, and players
        Stores results in the basic_parse member dictionary with team name as key

        :return: None
        """

        soup = self.get_soup(self.ranking_url)
        for team in soup.findAll('div', class_='ranked-team standard-box'):
            temp_dict = {}

            # Find basic team info
            name = (team.find('span', class_='name').text)
            rank = int(team.find('span', class_='position').text[1:])
            points = int(team.find('span', class_='points').text[1:-7])
            team_link = team.find('div', class_='more').find('a').get('href')
            try:
                id = re.search('team/(.+?)/', team_link).group(1)
            except AttributeError:
                # id not found
                print('{} team link and id are invalid'.format(name))
                id= 'Invalid'

            temp_dict = {'rank': rank, 'points': points, 'team_link': team_link, 'id': id}

            # Find player links for each member of the team
            for i, player in enumerate(team.findAll('td', class_='player-holder')):
                temp_dict['player_link' + str(i)] = player.find('a').get('href')

            self.basic_parse[name] = temp_dict

        return self.basic_parse


    def get_basic_match_info(self, team_name, days_old=365):
        """
        Given team name and time frame returns a dictionary of dates, maps, opponents and results for the team
        in the given time frame.

        :param team_name: name of the CS:GO team
        :param days_old: how many days back matches should be fetched (default=365)
        :return: a dictionary containing the gathered match info
        """

        # Link to many results from past few months
        matches_link = '/stats/teams/matches/' + self.basic_parse[team_name]['id'] + '/' + team_name
        soup = self.get_soup(matches_link)

        dates = []
        opponents = []
        maps = []
        results = []

        # get all available matches
        table = soup.find('table', {'class': 'stats-table no-sort'}).tbody
        for row in table.find_all('tr'):

            try:
                date_unparsed = row.find('td', class_='time').a.text
                date_ = datetime.strptime(date_unparsed, '%d/%m/%y')
                if (datetime.now() - date_).days > days_old:  # checks that match is not older than specified
                    break

                map_unparsed = row.find('td', class_='statsMapPlayed').text
                if map_unparsed not in self.map_translate:  # checks that map is active duty
                    continue
                map_ = self.map_translate[map_unparsed]

                opponent_ = row.contents[7].a.text
                try:
                    win_or_loss = row.find('td', class_='text-center match-won won').text
                    result_ = True
                except:
                    result_ = False


                dates.append(date_)
                opponents.append(opponent_)
                maps.append(map_)
                results.append(result_)

            except Exception as e:
                raise e
                print('EXCEPTION FOR: ', opponent_)
                # Maybe add logging in the future
                # print('Could not parse {}'.format(row))
                continue

        match_dict = {'dates': dates,
                      'opponents': opponents,
                      'maps': maps,
                      'results': results}

        return match_dict


    def get_dated_stats(self, team_name, opp_name, map, date, num_months=3):

        if not isinstance(num_months, int) or num_months > 18:
            raise Exception('num_months must be an integer <= 18')

        end_date = date - timedelta(days=1) #gather data one day up to match
        start_date = end_date - timedelta(days=(num_months * 30))
        end_date_string = end_date.strftime('%Y-%m-%d')
        start_date_string = start_date.strftime('%Y-%m-%d')


        link_modifiers = '?startDate=' + start_date_string + '&endDate=' + end_date_string + '&maps=' + \
                         map + '&rankingFilter=Top30'
        team_link = '/stats/teams/' + self.basic_parse[team_name]['id'] + '/' + team_name + link_modifiers


        team_stats = self.get_stats(team_link, opp=False)

        #Not sure how to handle the team id issue
        #For now I am going to just use teams that are in top30 since I have their ids.
        if opp_name not in self.basic_parse:
            #raise Exception('{} is not in top30')
            opp_link = team_link
            opp_stats = self.get_stats(opp_link, opp=True)
            team_stats.update(opp_stats)
            return team_stats, True

        else:
            opp_link = '/stats/teams/' + self.basic_parse[opp_name]['id'] + '/' + opp_name + link_modifiers
            opp_stats = self.get_stats(opp_link, opp=True)
            team_stats.update(opp_stats)
            return team_stats, False


    def get_stats(self, link, opp=False):
        """
        Goes through the stat page on hltv for a team and stores data in dictionary

        :param link: results on map by team
        :param opp: true if link is to opposing teams stats
        :return: stats: a parsed dict of the stats
        """

        if '/stats/teams/' not in link:
            return None
        soup = self.get_soup(link)

        stats = {}
        for stat in soup.findAll('div', class_='col standard-box big-padding'):

            y =stat.find('div', class_='large-strong').text
            x = stat.find('div', class_='small-label-below').text
            #print('X: ', x, '\tY: ', y)


            if x == 'Wins / draws / losses':
                wins = y.split('/')[0]
                losses = y.split('/')[2]
                if opp:
                    stats['O_Wins'] = int(wins)
                    stats['O_Losses'] = int(losses)
                else:
                    stats['Wins'] = int(wins)
                    stats['Losses'] = int(losses)

            else:
                if opp:
                    x = 'O_' + x


                if '.' in y:
                    stats[x] = float(y)
                elif y == '-':             # correction for undefined data points (ex K/D when deaths = 0)
                    stats[x] = ' '
                    #stats[x] = 0
                else:
                    stats[x] = int(y)

        return(stats)


    def export_df(self, path, df):

        export_csv = df.to_csv(path, index=None, header=True)


    def get_df(self):
        self.get_basic_parse()

        df = pd.DataFrame()
        for i, key in enumerate(self.basic_parse):

            print(i)
            print('Team: ', key)

            matchups = self.get_basic_match_info(key, 45)
            stats = self.get_formatted_stats(key, matchups)
            # for key in stats:
            #     print('Key: ', key, '\tLen: ', len(stats[key]))

            if len(stats['maps']) > 0:
                temp_df = pd.DataFrame(stats)
                df = pd.concat([df, temp_df])

            if i >=4:
                break

        print(df.head())
        print(df.info())
        self.export_df('C:\\Users\\solon\\PycharmProjects\\HLTV_Scraper\\df.csv', df)


    def get_formatted_stats(self, team_name, match_dict):
        """

        :param match_dict:
        :return:
        """

        return_dict = {}
        first_dict = True
        for i in range(len(match_dict['dates'])):

            stat_dict, opp_status = self.get_dated_stats(team_name,
                                             match_dict['opponents'][i],
                                             match_dict['maps'][i],
                                             match_dict['dates'][i])

            if opp_status:
                print('Stat Dict: ', stat_dict)
                match_dict['maps'][i] = 'false'
            # if stat_dict is None:
            #     for key in match_dict:
            #         del match_dict_copy[key][i]
            #     print('Not adding match between {} and {}'.format(team_name, match_dict['opponents'][i]))
            #     continue

            if first_dict:
                first_dict = False
                for key in stat_dict:
                    return_dict[key] = []
                    return_dict[key].append(stat_dict[key])

            else:
                for key in stat_dict:
                    return_dict[key].append(stat_dict[key])

        return_dict.update(match_dict)
        return return_dict

    # def remove_key(self, d, key, idx):
    #     r = dict(d)
    #     del r[key][idx]
    #     return r
##### CODE I PROB DONT NEED #####



    def get_match_history(self, team_name):

        if team_name in self.basic_parse:
            team_link = self.basic_parse[team_name]['team_link']
            team_soup = self.get_soup(team_link)
            links = self.get_match_links(team_soup)

            for link in links:
                print(link)
                #return self.get_soup(link)
                #break  # Only parse one link
        else:
            raise Exception('{} is not in top30 teams'.format(team_name))


    def get_match_links(self, soup):

        table = soup.find('table', {'class': 'match-table'})
        matches = table.find_all('td', {'class': 'stats-button-cell'})
        match_links = [match.find('a').get('href') for match in matches]
        return match_links


    def create_stat_link(self, team_link):

        if re.match('(/team/)([0-9][0-9]*[0-9]*[0-9]*[0-9]*/)(\w+)', team_link):
            stat_link = '/stats/teams' + team_link[5:]
            return stat_link
        else:
            return 'Invalid Link'