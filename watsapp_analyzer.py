import streamlit as st
import re
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud  # Make sure you import WordCloud from wordcloud library
from collections import Counter
import emoji
import seaborn as sns


st.sidebar.title("WhatsApp Chat Analyzer")

def preprocess(data):
    pattern = r'\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}\s-\s'
    messages = re.split(pattern, data)[1:]
    dates = re.findall(pattern, data)
    df = pd.DataFrame({'user_message': messages, 'message_date': dates})
    
    # Convert message_date type
    df['message_date'] = pd.to_datetime(df['message_date'], format='%d/%m/%Y, %H:%M -  ')
    
    df.rename(columns={'message_date': 'date'}, inplace=True)

    users = []
    messages = []
    for message in df['user_message']:
        entry = re.split('([\w\W]+?):\s', message)
        if entry[1:]:  # user name
            users.append(entry[1])
            messages.append(entry[2])
        else:
            users.append('group_notification')
            messages.append(entry[0])

    df['user'] = users
    df['message'] = messages
    df.drop(columns=['user_message'], inplace=True)

    df['only_date'] = df['date'].dt.date
    df['year'] = df['date'].dt.year
    df['month_num'] = df['date'].dt.month
    df['month'] = df['date'].dt.month_name()
    df['day'] = df['date'].dt.day
    df['hour'] = df['date'].dt.hour
    df['minute'] = df['date'].dt.minute
    df['day_name'] = df['date'].dt.day_name()

    period = []
    for hour in df['hour']:
        if hour == 23:
            period.append(str(hour) + "-" + "00")
        else:
            period.append(str(hour) + "-" + str(hour + 1))

    df['period'] = period

    return df


from urlextract import URLExtract
extract=URLExtract()


def fetch_stats(selected_user, df):
    if selected_user == 'Overall':
        # Fetch number of messages
        num_messages = df.shape[0]
        
        # Fetch number of words
        words = [word for message in df['message'] for word in message.split()]
        
        # Fetch number of media messages
        num_media_messages = df[df['message'] == '<Media omitted>\n'].shape[0]

        # Fetch number of links shared
        links = []
        for message in df['message']:
            links.extend(extract.find_urls(message))

        return num_messages, len(words), num_media_messages, len(links)
    else:
        new_df = df[df['user'] == selected_user]
        num_messages = new_df.shape[0]
        words = [word for message in new_df['message'] for word in message.split()]
        num_media_messages = df[df['message'] == '<Media omitted>\n'].shape[0]
        links = [0]
        for message in df['message']:
            links.extend(extract.find_urls(message))
        return num_messages, len(words), num_media_messages, links
    
def most_busy_users(df):
    x=df['user'].value_counts().head()
    df=round((df['user'].value_counts()/df.shape[0])*100,2).reset_index().rename(columns={'index':'name','user':'percent'})
    return x,df


def create_wordcloud(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    wc = WordCloud(width=500, height=500, min_font_size=10, background_color='white')
    df_wc = wc.generate(df['message'].str.cat(sep=" "))
    return df_wc

def most_common_words(selected_user,df):
    f=open('stop_hinglish.txt','r')
    stop_words=f.read()

    if selected_user!='Overall':
        df=df[df['user']==selected_user]

    temp=df[df['user']!='group_notification']
    temp=temp[temp['message']!='<Media omitted>\n']

    words=[]

    for message in temp['message']:
        for word in message.lower().split():
            if word not in stop_words:
                words.append(word)
    most_common_df = pd.DataFrame(Counter(words).most_common(20))
    return most_common_df

def emoji_helper(selected_user,df):
    if selected_user != 'Overall':
        df=df[df['user'] == selected_user]

    emojis = []
    for message in df['message']:
        emojis.extend([c for c in message if emoji.emoji_count(c) > 0])

    emoji_df= pd.DataFrame(Counter(emojis).most_common(len(Counter(emojis))))

    return emoji_df

def monthly_timeline(selected_user,df):
    if selected_user != 'Overall':
       df=df[df['user'] == selected_user]
    timeline= df.groupby(['year','month_num','month']).count()['message'].reset_index()

    time=[]
    for i in range(timeline.shape[0]):
        time.append(timeline['month'][i] + "-" + str(timeline['year'][i]))
    timeline['time']=time

    return timeline

def daily_timeline(selected_user,df):

   if selected_user != 'Overall':
       df=df[df['user'] == selected_user]

   daily_timeline= df.groupby('only_date').count()['message'].reset_index()

   return daily_timeline
   
def week_activity_map(selected_user,df):
    if selected_user != 'Overall':
       df=df[df['user'] == selected_user]

    return df['day_name'].value_counts()

def month_activity_map(selected_user,df):
    if selected_user != 'Overall':
       df=df[df['user'] == selected_user]

    return df['month'].value_counts()

def activity_heatmap(selected_user,df):
    if selected_user!= "Overall":
        df=df[df['user'] == selected_user]

    user_heatmap= df.pivot_table(index='day_name',columns='period',values='message',
                                   aggfunc='count').fillna(0)
    
    return user_heatmap



uploaded_file = st.sidebar.file_uploader("Choose a file")
if uploaded_file is not None:
    bytes_data = uploaded_file.getvalue()
    data = bytes_data.decode("utf-8")
    df = preprocess(data)

    st.dataframe(df)

    # Fetch unique users
    user_list = df['user'].unique().tolist()
    user_list.remove('group_notification')
    user_list.sort()
    user_list.insert(0, "Overall")

    selected_user = st.sidebar.selectbox("Show analysis wrt", user_list)

if st.sidebar.button("Show Analysis"):
    num_messages, words, num_media_messages, num_links = fetch_stats(selected_user, df)
    st.title("Top Stats")

    col1, col2, col3, col4 = st.columns(4)


    with col1:
        st.header("Total Messages")
        st.title(num_messages)
    with col2:
        st.header("Total Words")
        st.title(words)
    with col3:
        st.header("Media Shared")
        st.title(num_media_messages)
    with col4:
        st.header("Links Shared")
        st.title(num_links)


    #timeline
       

        st.title("Monthly Timeline")
        timeline = monthly_timeline(selected_user, df) 
        fig, ax = plt.subplots()  # Set figure size here
        ax.plot(timeline['time'], timeline['message'],color='green')
        plt.xticks(rotation='vertical')
        st.pyplot(fig)

#daily timeline
        st.title("Daily Timeline")
        daily_timeline = daily_timeline(selected_user, df) 
        fig, ax = plt.subplots()  # Set figure size here
        ax.plot(daily_timeline['only_date'],daily_timeline['message'],color='black')
        plt.xticks(rotation='vertical')
        st.pyplot(fig)

#Weekly activity
        st.title('Activity Map')
        col1,col2= st.columns(2)

        with col1:
            st.header("Most busy day")
            busy_day=week_activity_map(selected_user,df)
            fig,ax=plt.subplots()
            ax.bar(busy_day.index, busy_day.values)
            plt.xticks(rotation='vertical')

            st.pyplot(fig)

#Month activity
        with col2:
            st.header("Most busy month")
            busy_month=month_activity_map(selected_user,df)
            fig,ax=plt.subplots()
            ax.bar(busy_month.index, busy_month.values,color='orange')
            plt.xticks(rotation='vertical')
            st.pyplot(fig)

        st.title("Weekly Activity Map")
        user_heatmap =activity_heatmap(selected_user,df)
        fig,ax=plt.subplots()
        ax=sns.heatmap(user_heatmap)
        st.pyplot(fig)


#finding the busiest users in the group
    if selected_user=='Overall':
        st.title('Most Busy User')
        x,new_df=most_busy_users(df)
        fig,ax=plt.subplots()

        col1,col2=st.columns(2)
 
        with col1:
            ax.bar(x.index,x.values,color='red')
            plt.xticks(rotation='vertical')
            st.pyplot(fig)
        with col2:
            st.dataframe(new_df)

    # wordcloud
    df_wc=create_wordcloud(selected_user,df)
    fig,ax=plt.subplots()
    ax.imshow(df_wc)
    st.pyplot(fig)

    #Most common word

    most_common_df=most_common_words(selected_user,df)

    fig,ax= plt.subplots()
    ax.barh(most_common_df[0],most_common_df[1])
    plt.xticks(rotation='vertical')
    st.title('Most Common Words')

    st.pyplot(fig)

    #st.dataframe(most_common_df)

    ##emoji analysis
    emoji_df=emoji_helper(selected_user,df)
    st.title("Emoji Analysis")

    col1,col2=st.columns(2)

    with col1:
        st.dataframe(emoji_df)
    with col2:
        fig,ax=plt.subplots()
        ax.pie(emoji_df[1].head(),labels=emoji_df[0].head(),autopct="%0.2f")
        st.pyplot(fig)
    # st.dataframe(emoji_df)