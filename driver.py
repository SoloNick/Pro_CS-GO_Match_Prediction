from HLTV_Scraper import hltvScraper

def main():

    #stuff
    data_gen = hltvScraper()
    temp = data_gen.get_basic_parse()
    #print(temp['Astralis'])
    #a = (data_gen.get_basic_match_info('Astralis', 45))
    data_gen.get_df()
    #
    # for i in range(len(a['dates'])):
    #
    #     data_gen.get_dated_stats('Astralis', a['opponents'][i], a['maps'][i], a['dates'][i])
    #
    #     #print('Opponent\t', a['opponents'][i])
    #     break

    #b = (data_gen.get_match_history('Astralis'))
    #print(data_gen.get_team_stats('/team/6665/astralis'))
    #df = data_gen.get_match_history('Astralis')
    #print(df)

if __name__ == '__main__':

    main()