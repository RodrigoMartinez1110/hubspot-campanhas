import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import locale

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')  # Alternativa compatível

st.set_page_config(layout="wide")
st.title('Analisar Geração de Leads')



# Adicionar opção para considerar ou não dias úteis
considerar_dias_uteis = st.sidebar.checkbox("Considerar apenas dias úteis", value=True)


def tratar_arquivo_hubspot(dataframe):
    # Tratamento de dados
    mapa_colunas = {
        'ID do registro.': 'id',
        'Nome do negócio': 'nome',
        'Data de criação': 'data_criado',
        'CPF': 'cpf',
        'Telefone': 'telefone',
        'Convênio': 'convenio',
        'Origem': 'origem',
        'Campanha': 'tag_campanha',
        'Proprietário original do negócio': 'vendedor',
        'Tipo de Campanha': 'produto',
        'Equipe da HubSpot': 'equipe',
        'Etapa do negócio': 'etapa',
        'Motivo de fechamento perdido': 'motivo_fechamento',
        'Comissão total projetada': 'comissao_projetada',
        'Valor': 'comissao_gerada',
        'Proprietário do negócio': 'vendedor2',
        'Date entered "CONTRATAÇÃO ( Pipeline de Vendas)"': 'data_contratacao',
        'Date entered "LEAD ( Pipeline de Vendas)"': 'data_lead',
        'Date entered "NEGOCIAÇÃO ( Pipeline de Vendas)"': 'data_negociacao',
        'Date entered "PAGO ( Pipeline de Vendas)"': 'data_pago',
        'Date entered "PERDA ( Pipeline de Vendas)"': 'data_perda',
        'Detalhes do motivo de perda': 'detalhe_perda'
    }

    dataframe.columns = dataframe.columns.map(mapa_colunas)

    motivos_principais = ['Sem Interação', 'Telefone Inválido', 'Sem interesse', 'Sem oportunidade',
                          'Lead respondeu "NÃO" ao disparo', 'Vínculo inadequado', 'Desistência do Cliente',
                          'Sem interação; Sem interesse', 'Não atende', 'Não receber mensagens - LGPD',
                          'Margem Insuficiente']
    # Criar uma nova coluna com os motivos agrupados
    dataframe['motivo_fechamento_agrupado'] = dataframe['motivo_fechamento'].apply(
        lambda x: x if x in motivos_principais else 'Outros'
    )

    def criar_acronimo(convenio):
        if isinstance(convenio, str):  # Verificar se 'convenio' é uma string
            convenio = convenio.lower()  # Usar .lower() diretamente
        else:
            convenio = ''  # Ou algum valor padrão caso não seja uma string
        mapeamento = {
            'prefeitura de recife': 'PREF REC',
            'prefeitura de curitiba': 'PREF CUR',
            'prefeitura de maringá': 'PREF MAR',
            'prefeitura de goiânia': 'PREF GOI',
            'prefeitura de belo horizonte': 'PREF BH',
            'governo de rondônia': 'GOV RO',
            'governo do paraná': 'GOV PR',
            'prefeitura de são paulo': 'PREF SP',
            'governo de são paulo': 'GOV SP',
            'prefeitura do rio de janeiro': 'PREF RJ',
            'governo do rio de janeiro': 'GOV RJ',
            'prefeitura de salvador': 'PREF SSA',
            'governo da bahia': 'GOV BA',
            'governo de alagoas': 'GOV AL',
            'governo do amazonas': 'GOV AM',
            'governo do maranhão': 'GOV MA',
            'governo de goiás': 'GOV GO',
            'governo do ceará': 'GOV CE',
            'governo de pernambuco': 'GOV PE',
            'governo de mato grosso do sul': 'GOV MS',
            'governo de mato grosso': 'GOV MT',
            'governo do piauí': 'GOV PI',
            'prefeitura de joão pessoa': 'PREF JP'
        }
        
        return mapeamento.get(convenio, convenio)
    dataframe['convenio_acronimo'] = dataframe['convenio'].apply(criar_acronimo)

    dataframe.loc[dataframe['equipe'].str.contains('Sales', case=False, na=False), 'equipe'] = 'Sales'
    dataframe.loc[dataframe['equipe'].str.contains('Cs Ativação', case=False, na=False), 'equipe'] = 'Cs Ativacao'
    dataframe.loc[dataframe['equipe'].str.contains('Cs App', case=False, na=False), 'equipe'] = 'Cs App'

    
    dataframe['data_criado'] = pd.to_datetime(dataframe['data_criado'], errors='coerce')
    dataframe['data'] = dataframe['data_criado'].dt.date
    dataframe['horario_criado'] = dataframe['data_criado'].dt.time
    dataframe.drop(columns=['data_criado'], inplace=True)

    dataframe['data_lead'] = pd.to_datetime(dataframe['data_lead'], errors='coerce').dt.date
    dataframe['data_negociacao'] = pd.to_datetime(dataframe['data_negociacao'], errors='coerce').dt.date
    dataframe['data_contratacao'] = pd.to_datetime(dataframe['data_contratacao'], errors='coerce').dt.date
    dataframe['data_pago'] = pd.to_datetime(dataframe['data_pago'], errors='coerce').dt.date
    
    return dataframe

def tratar_arquivo_pagos(dataframe):
    dataframe['data'] = pd.to_datetime(dataframe['Data'], errors='coerce', dayfirst=True).dt.date
    dataframe['Valor Gasto'] = (dataframe['Canal'].map({'SMS': 0.047, 'RCS': 0.105}) * dataframe['Quantidade']).round(2)
    return dataframe

# Carregar dados
st.sidebar.title('Carregar dados')
dados = st.sidebar.file_uploader("Envie os arquivos CSV", type="csv", accept_multiple_files=True)

df = None
df_gasto = None

if dados:
    for arquivo in dados:
        nome_arquivo = arquivo.name.lower()
        if "hubspot" in nome_arquivo:
            df = pd.read_csv(arquivo)
            df = tratar_arquivo_hubspot(df)

        # Se o nome do arquivo contém "gasto", carregamos no df_gasto
        if "gasto" in nome_arquivo:
            df_gasto = pd.read_csv(arquivo, sep=';') 
            df_gasto = tratar_arquivo_pagos(df_gasto)

    
    st.sidebar.write('---')
    st.sidebar.title('Filtros')
    # Filtros
    with st.sidebar.expander('Equipe'):
        equipe_vendedores = df['equipe'].unique()
        equipe = st.multiselect('Equipe', equipe_vendedores)
        if not equipe:  # Se estiver vazio, considera todos
            equipe = equipe_vendedores

    with st.sidebar.expander('Produtos'):
        produtos = df['produto'].unique()
        produto = st.multiselect('Produto', produtos)
        if not produto:  # Se estiver vazio, considera todos
            produto = produtos

    with st.sidebar.expander('Convenios'):
        convenios = df['convenio_acronimo'].unique()
        convenio = st.multiselect('Convenio', convenios)
        if not convenio:  # Se estiver vazio, considera todos
            convenio = convenios

    with st.sidebar.expander('Etapas'):
        etapas = df['etapa'].unique()
        etapa = st.multiselect('Etapa', etapas)
        if not etapa:  # Se estiver vazio, considera todos
            etapa = etapas
        
    with st.sidebar.expander("Origem"):
        origens = df['origem'].unique()
        origem = st.multiselect('Canal', origens)
        if not origem:  # Se estiver vazio, considera todos
            origem = origens

    with st.sidebar.expander('Filtro Data'):
        data_inicio = st.date_input('Data de início', min_value=df['data'].min(), max_value=df['data'].max(), value=df['data'].min())
        data_fim = st.date_input('Data de fim', min_value=df['data'].min(), max_value=df['data'].max(), value=df['data'].max())

    df_filtrado = df.copy()
    
    df_filtrado = df_filtrado[(df_filtrado['data'] >= data_inicio) & (df_filtrado['data'] <= data_fim)]
    df_filtrado = df_filtrado.loc[df_filtrado['equipe'].isin(equipe)]
    df_filtrado = df_filtrado.loc[df_filtrado['produto'].isin(produto)]
    df_filtrado = df_filtrado.loc[df_filtrado['convenio_acronimo'].isin(convenio)]
    df_filtrado = df_filtrado.loc[df_filtrado['etapa'].isin(etapa)]
    df_filtrado = df_filtrado.loc[df_filtrado['origem'].isin(origem)]

    df_gasto = df_gasto.loc[df_gasto['Convênio'].isin(convenio)]
    df_gasto = df_gasto[(df_gasto['data'] >= data_inicio) & (df_gasto['data'] <= data_fim)]
    df_gasto = df_gasto.loc[df_gasto['Produto'].isin(produto)]
    df_gasto = df_gasto.loc[df_gasto['Canal'].isin(origem)]
    df_gasto = df_gasto.loc[df_gasto['Equipe'].isin(equipe)]
    
    # Função para filtrar dias úteis
    def filtrar_dias_uteis(df, data_inicio, data_fim):
        if considerar_dias_uteis:
            dias_uteis = pd.bdate_range(start=data_inicio, end=data_fim)
            return df[df['data'].isin(dias_uteis.date)]
        return df

    
    # Aplicar filtro de dias úteis
    df_filtrado = filtrar_dias_uteis(df_filtrado, data_inicio, data_fim)
    df_gasto = filtrar_dias_uteis(df_gasto, data_inicio, data_fim)

    # KPI's
    st.markdown("""<style>
        .kpi-container {
            background-color: #004E64;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
            width: 220px;
            height: 130px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .kpi-title {
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
        }
        .kpi-value {
            font-size: 18px;
            font-weight: bold;
            color: #ffffff;
        }
        .kpi-delta-positive {
            font-size: 14px;
            color: #9FFFCB;
        }
        .kpi-delta-negative {
            font-size: 14px;
            color: #FCB9B2;
        }
        </style>
    """, unsafe_allow_html=True)

    gastos = df_gasto.groupby(['Convênio', 'Produto', 'Canal'])['Quantidade'].sum().reset_index()
    gastos['valor_pago'] = gastos['Canal'].map({'SMS': 0.048, 'RCS': 0.105}) * gastos['Quantidade']
    
    
    # Exibindo os resultados com Streamlit
    col1, col2, col3, col4, col5, col6 = st.columns(6)


    
    #Total de leads gerados
    with col1:
        total_leads_gerados = df.shape[0]  # Contagem total de leads gerados
        total_gerado_filtrado = df_filtrado.shape[0]  # Contagem total de leads gerados após o filtro
        st.markdown('<div class="kpi-container"><div class="kpi-title">Total de Leads Gerados</div><div class="kpi-value">'+str(total_gerado_filtrado)+'</div></div>', unsafe_allow_html=True)

    if total_gerado_filtrado == 0:
        total_gerado_filtrado = 0.1
    #Média de leads gerados por dia
    with col2:
        if considerar_dias_uteis:
            # Gerar a lista de dias úteis entre as datas
            dias_uteis = pd.bdate_range(start=data_inicio, end=data_fim)
        else:
            # Caso não considerar dias úteis, usar todos os dias no intervalo
            dias_uteis = pd.date_range(start=data_inicio, end=data_fim)

        # Calcular a média de leads gerados por dia útil
        if len(dias_uteis) > 0:  # Verifica se existem dias úteis no intervalo
            media_leads_gerados_dia = total_gerado_filtrado / len(dias_uteis)
            media_leads_gerados_dia = round(media_leads_gerados_dia, 2)

            # Calcular o delta entre as médias
            delta_media_leads = media_leads_gerados_dia

            # Definir a classe de delta (verde para positivo, vermelho para negativo)
            delta_class = 'kpi-delta-positive' if delta_media_leads >= 0 else 'kpi-delta-negative'

            # Exibir o KPI com o delta de variação
            st.markdown(f'<div class="kpi-container"><div class="kpi-title">Média de Leads Gerados</div>'
                        f'<div class="kpi-value">{media_leads_gerados_dia}</div>'
                        f'<div class="{delta_class}">Variação: {delta_media_leads:+.2f}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="kpi-container"><div class="kpi-title">Média de Leads Gerados</div>' '<div class="kpi-value">0</div></div>', unsafe_allow_html=True)
    
    #Taxa de conversão
    with col3:
        media_taxa_conversao = df.query('etapa == "PAGO"').shape[0] / total_leads_gerados
        media_taxa_conversao = round(media_taxa_conversao * 100, 2)

        taxa_conversao_filtrado = df_filtrado.query('etapa == "PAGO"').shape[0] / total_gerado_filtrado
        taxa_conversao_filtrado = round(taxa_conversao_filtrado * 100, 2)
        # Comparação entre as taxas de conversão geral e filtrada
        delta_taxa = taxa_conversao_filtrado - media_taxa_conversao
        
        # Escolher a classe CSS com base no sinal do delta
        delta_class = 'kpi-delta-positive' if delta_taxa >= 0 else 'kpi-delta-negative'
        
        st.markdown(f'<div class="kpi-container"><div class="kpi-title">Taxa de Conversão</div><div class="kpi-value">{taxa_conversao_filtrado}%</div><div class="{delta_class}">Variação: {delta_taxa:+.2f}%</div></div>', unsafe_allow_html=True)

    #Valor total gerado
    with col4:
        valor_total_gerado = df_filtrado['comissao_gerada'].sum()
        valor_formatado = f"R$ {valor_total_gerado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")  # Formatação BR
        st.markdown(f'<div class="kpi-container"><div class="kpi-title">Valor Total Gerado</div><div class="kpi-value">{valor_formatado}</div></div>', unsafe_allow_html=True)

    with col5:
        valor_gasto_total = round(gastos['valor_pago'].sum(), 2)
        valor_formatado = f"R$ {valor_gasto_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")  # Formatação BR
        st.markdown(f'<div class="kpi-container"><div class="kpi-title">Valor Total Gasto</div><div class="kpi-value">{valor_formatado}</div></div>', unsafe_allow_html=True)

    with col6:
        lucro = round(valor_total_gerado - valor_gasto_total, 2)
        valor_formatado = f"R$ {lucro:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")  # Formatação BR
        delta_taxa = valor_total_gerado - valor_gasto_total
        delta_class = 'kpi-delta-positive' if delta_taxa >= 0 else 'kpi-delta-negative'
        st.markdown(f'<div class="kpi-container"><div class="kpi-title">Lucro Bruto</div><div class="kpi-value">{valor_formatado}</div></div>', unsafe_allow_html=True)

    
    with st.expander("Gasto por Convênio e Produto"):
        # Seletor para número de convênios
        top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=10, step=1)

        df_filtrado_temp = df_filtrado.loc[df_filtrado['etapa'] == 'PAGO']
        
        gasto_convenios = df_gasto.groupby(['Convênio', 'Produto'])['Valor Gasto'].sum().reset_index(name='gasto_total')
        gerado_convenios = df_filtrado_temp.groupby(['convenio_acronimo', 'produto'])['comissao_gerada'].sum().reset_index(name='comissao_gerada')
        
        gasto_convenios.rename(columns={
            'Convênio': 'convenio_acronimo',
            'Produto': 'produto',
        }, inplace=True)
        
        convenios_completo = pd.merge(
            gasto_convenios,
            gerado_convenios,
            on=['convenio_acronimo', 'produto'],
            how='outer'
        )

        convenios_completo[['gasto_total', 'comissao_gerada']] = convenios_completo[['gasto_total', 'comissao_gerada']].fillna(0)
        convenios_completo = convenios_completo.sort_values(by='comissao_gerada', ascending=False)
        
        # Aplicando o filtro de top N
        convenios_completo = convenios_completo.head(top_n)

        convenios_completo['conv_prod'] = convenios_completo['convenio_acronimo'] + ' - ' + convenios_completo['produto']

        df_long = pd.melt(
            convenios_completo,
            id_vars='conv_prod',
            value_vars=['comissao_gerada', 'gasto_total'],
            var_name='tipo',
            value_name='valor'
        )

        fig = px.bar(
            df_long,
            x='valor',
            y='conv_prod',
            color='tipo',
            barmode='group',
            labels={'conv_prod': 'Convênio - Produto', 'valor': 'Valor (R$)', 'tipo': 'Tipo de Valor'},
            text='valor'
        )

        fig.update_traces(
            textposition='outside',
            textfont=dict(size=20, color='white')
        )

        fig.update_layout(
            height=1000,
            width=1800,
            xaxis_tickangle=-50,
            bargap=0.4,
            bargroupgap=0.2,
            xaxis=dict(
                tickfont=dict(size=18)
            )
        )

        st.plotly_chart(fig)
    
    #Gráfico de leads gerados por convênio
    with st.expander("Geração de leads"):
        mapa_cores = {
            "Novo": "#1f77b4",               # azul claro
            "Cartão": "#ff7f0e",             # laranja vibrante
            "Benefício": "#2ca02c",          # verde claro
            "Benefício e Cartão": "#d62728", # vermelho vibrante
            "Port": "#9467bd"                # roxo claro
        }
            
        col1, col2 = st.columns(2)
        with col1:
            # Gráfico de leads gerados por convênio
            quantidade = df_filtrado.groupby(['convenio_acronimo']).size().reset_index(name='quantidade_total')
            grouped = df_filtrado.groupby(['convenio_acronimo', 'produto']).size().reset_index(name='quantidade')
            grouped = pd.merge(quantidade, grouped, on='convenio_acronimo', how='left').sort_values(by='quantidade_total', ascending=False)
            graf1 = px.bar(
                grouped,
                x='quantidade',
                y='convenio_acronimo',
                color='produto',
                title='Leads Gerados por Convênio',
                color_discrete_map=mapa_cores
            )
            graf1.update_layout(
                title='1. Leads Gerados por Convênio',
                xaxis_title='Quantidade',
                font=dict(size=16),
                yaxis_title='Convênio',
                legend_title='Produto',
                xaxis_tickfont_size=12,
                height=900,
                width=800,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            st.plotly_chart(graf1)

        #Gráfico de leads gerados por dia por produto
        with col2:
            # Agrupando as quantidades de leads por data e produto (convênio)
            quantidade_dia_produto = df_filtrado.groupby(['data', 'produto']).size().reset_index(name='quantidade')

            # Agrupando a quantidade total de leads por dia
            quantidade_dia_total = df_filtrado.groupby('data').size().reset_index(name='quantidade_total')

            # Se considerar apenas dias úteis, filtrar os dados
            if considerar_dias_uteis:
                dias_uteis = pd.bdate_range(start=data_inicio, end=data_fim)
                quantidade_dia_produto = quantidade_dia_produto[quantidade_dia_produto['data'].isin(dias_uteis.date)]
                quantidade_dia_total = quantidade_dia_total[quantidade_dia_total['data'].isin(dias_uteis.date)]

            # Criando o gráfico de barras empilhadas
            fig2 = px.bar(
                quantidade_dia_produto,
                x='data',
                y='quantidade',
                color='produto',
                title='Leads Gerados por Dia por Produto',
                barmode='stack',
                text='quantidade',
                color_discrete_map=mapa_cores
            )
            # Adicionando a linha para a quantidade total de leads por dia
            fig2.add_trace(go.Scatter(
                x=quantidade_dia_total['data'],
                y=quantidade_dia_total['quantidade_total'],
                line=dict(color='#8B5CF6', width=3),
                line_shape='spline',
                mode='lines+markers',
                name='Total de Leads',
                marker=dict(size=6),
                hovertemplate='<b>Data:</b> %{x}<br>'  # Exibe a data
                            + '<b>Total de Leads:</b> %{y}<extra></extra>',  # Exibe a quantidade total
            ))

            # Atualizando o layout do gráfico
            fig2.update_layout(
                title='2. Leads Gerados por Dia por Produto',
                xaxis_title='Data',
                yaxis_title='Quantidade de Leads',
                legend=dict(font=dict(size=10)),
                xaxis_tickfont_size=12,
                height=900,
                width=800,
                bargap=0.1,  # Reduz o espaço entre as barras
                bargroupgap=0.2,  # Ajusta o espaçamento entre os grupos de barras
                margin=dict(l=0, r=10, t=25, b=0),
                showlegend=True
            )

            # Exibindo o gráfico no Streamlit
            st.plotly_chart(fig2)



    with st.expander("Perda de Leads"):
        col1, col2 = st.columns(2)

        #Gráfico de leads perdidos por convênio
        with col1:
            # Filtrar leads perdidos
            leads_perdidos = df_filtrado[df_filtrado['etapa'] == 'PERDA']
            leads_perdidos = leads_perdidos.groupby(['convenio_acronimo', 'motivo_fechamento_agrupado'])['id'].count().reset_index(name='quantidade').sort_values(by='quantidade', ascending=False)
            try:
                leads_perdidos['quantidade_gerada'] = total_gerado_filtrado  # Usando o total filtrado
                leads_perdidos['porcentagem'] = leads_perdidos['quantidade'] / total_gerado_filtrado * 100
            except ZeroDivisionError:
                leads_perdidos['quantidade_gerada'] = total_gerado_filtrado  # Usando o total filtrado
                total_gerado_filtrado = 1
                leads_perdidos['porcentagem'] = leads_perdidos['quantidade'] / total_gerado_filtrado * 100
            graf3 = px.bar(
                leads_perdidos,
                x='convenio_acronimo',
                y='quantidade',
                title='TOP 5 convênios com mais leads perdidos'
            )

            # Atualizar layout
            graf3.update_layout(
                title='3. TOP 5 convênios com mais leads perdidos',
                xaxis_title='Convênio',
                yaxis_title='Quantidade de Leads',
                legend_orientation='h',
                legend_y=1.1,
                showlegend=False,
                xaxis_tickfont_size=12,
                height=550,
                width=600,
                margin=dict(l=0, r=10, t=40, b=0)
            )

            # Atualizar traces para incluir motivo_fechamento_agrupado no hover
            graf3.update_traces(
                hovertemplate="Convênio: %{x}<br>" +  
                            "Leads perdidos: %{y}<br>" +  
                            "Motivo: %{customdata[0]}<br>" +  # Exibir o motivo de fechamento
                            "Total de leads gerados: " + str(total_gerado_filtrado) + "<br>" +
                            "Porcentagem: %{customdata[1]:.1f}%<extra></extra>",
                customdata=leads_perdidos[['motivo_fechamento_agrupado', 'porcentagem']].values  # Passar os dados adicionais
            )

            
            st.plotly_chart(graf3)
        
        #Gráfico de leads perdidos por motivo
        with col2:              
            leads_perdidos = df_filtrado[df_filtrado['etapa'] == 'PERDA']
            leads_perdidos = leads_perdidos.groupby(['motivo_fechamento'])['id'].count().reset_index(name='quantidade').sort_values(by='quantidade', ascending=False).head(5)
            leads_perdidos['porcentagem'] = leads_perdidos['quantidade'] / total_gerado_filtrado * 100  # Usando o total filtrado
            
            graf4 = px.bar(
                leads_perdidos,
                x="motivo_fechamento",
                y="quantidade",
                title="TOP 5 motivos de perda",
                color="porcentagem",
                text=leads_perdidos["porcentagem"].map(lambda x: f"{x:.1f}%")  # Exibir a porcentagem nas barras
            ) 

            graf4.update_traces(
                hovertemplate="Motivo: %{y}<br>" +  # %{y} representa 'motivo_fechamento'
                "Leads perdidos: %{x}<br>" +  # %{x} representa 'quantidade'
                "Total de leads gerados: " + str(total_gerado_filtrado) + "<br>" +
                "Porcentagem: %{customdata:.1f}%<extra></extra>",  # %{customdata} para exibir a porcentagem
                customdata=leads_perdidos["porcentagem"]  # Passa a porcentagem para o hover
            )

            graf4.update_layout(
                title='3. TOP 5 motivos de perda',
                xaxis_title='',
                yaxis_title='Quantidade',
                legend_orientation='h',
                legend_y=1.1,
                xaxis_tickfont_size=12,
                height=600,
                width=750,
                margin=dict(l=30, r=10, t=30, b=0)
            )

            st.write(graf4)

    #Gráfico de Boxplot:  Comissão média por convenio dos leads gerados
    with st.expander("Comissão dos Leads Gerados"):
        graf5 = px.box(df_filtrado, x='convenio_acronimo', y='comissao_projetada', title='Comissão média dos leads gerados')

        graf5.update_layout(
                title='5. Comissão média por convenio dos leads gerados',
                xaxis_title='',
                yaxis_title='Quantidade',
                legend_orientation='h',
                legend_y=1.0,
                xaxis_tickfont_size=12,
                height=600,
                width=1300,
                margin=dict(l=30, r=10, t=40, b=0)
            )
        
        st.plotly_chart(graf5)

    
    with st.expander("Funil de Etapas dos Leads"):
        # Contagem por datas
        etapas = {
            'LEAD': df_filtrado['data'].notna().sum(),
            'NEGOCIAÇÃO': df_filtrado['data_negociacao'].notna().sum(),
            'CONTRATAÇÃO': df_filtrado['data_contratacao'].notna().sum(),
            'PAGO': df_filtrado['data_pago'].notna().sum(),
            'PERDA': df_filtrado['data_perda'].notna().sum()
        }

        df_funil = pd.DataFrame({
            'etapa': list(etapas.keys()),
            'quantidade': list(etapas.values())
        })

        # % em relação ao início do funil
        total_inicio = df_funil.loc[0, 'quantidade'] if df_funil.loc[0, 'quantidade'] > 0 else 1
        df_funil['pct_inicio'] = df_funil['quantidade'] / total_inicio * 100

        # Texto para mostrar dentro do gráfico
        df_funil['texto'] = df_funil.apply(
            lambda row: f"{row['quantidade']}\n({row['pct_inicio']:.1f}%)", axis=1
        )

        # Criar o gráfico com plotly express
        fig = px.funnel(
            df_funil,
            x='quantidade',
            y='etapa',
            text='texto',
            labels={'etapa': 'Etapa do Funil', 'quantidade': 'Leads'},
            color_discrete_sequence=["#00BFFF", "#1E90FF", "#6495ED", "#7B68EE", "#8A2BE2"]
        )

        # Atualiza layout e estilo
        fig.update_traces(
            textposition='auto',
            textfont_size=26,  # ← funciona aqui com px
            marker_line_width=1,
            marker_line_color='white'
        )

        fig.update_layout(
            title='5. Funil de Etapas do Hubspot',
            xaxis_title='',
            yaxis_title='Quantidade',
            legend_orientation='h',
            legend_y=1.0,
            xaxis_tickfont_size=12,
            height=800,
            width=1300,
            margin=dict(l=30, r=10, t=40, b=0)
        )

        st.plotly_chart(fig, use_container_width=True)


    with st.expander("Cohort - Eventos Dinâmicos"):
        df_cohort = df_filtrado.copy()
        
        # Converte colunas de data
        data_cols = ['data', 'data_negociacao', 'data_contratacao', 'data_pago', 'data_perda']
        for col in data_cols:
            df_cohort[col] = pd.to_datetime(df_cohort[col], errors='coerce')

        # Define os eventos disponíveis
        opcoes_evento = {
            "Pagamento": "data_pago",
            "Perda": "data_perda",
            "Negociação": "data_negociacao",
            "Contratação": "data_contratacao"
        }

        # Input do usuário para escolher o evento
        evento_escolhido = st.selectbox("Selecione o evento para análise de cohort:", list(opcoes_evento.keys()))
        coluna_evento = opcoes_evento[evento_escolhido]

        # Define cohort pela data de entrada
        df_cohort['cohort'] = df_cohort['data'].dt.date
        df_cohort['dias_ate_evento'] = (df_cohort[coluna_evento] - df_cohort['data']).dt.days

        # Filtra apenas quem teve o evento
        df_eventos = df_cohort.dropna(subset=['dias_ate_evento'])

        # Conta eventos por cohort e dia
        cohort_counts = df_eventos.groupby(['cohort', 'dias_ate_evento']).size().reset_index(name='quantidade')

        # Tamanho total de cada cohort
        cohort_sizes = df_cohort.groupby('cohort').size().to_dict()
        cohort_counts['tamanho_cohort'] = cohort_counts['cohort'].map(cohort_sizes)

        # Taxa de conversão
        cohort_counts['taxa'] = (cohort_counts['quantidade'] / cohort_counts['tamanho_cohort']) * 100

        # Formata label do eixo Y com total de leads
        cohort_counts['cohort_str'] = cohort_counts['cohort'].astype(str) + " (n=" + cohort_counts['tamanho_cohort'].astype(str) + ")"

        # Pivot para formato de matriz
        heatmap_data = cohort_counts.pivot(index='cohort_str', columns='dias_ate_evento', values='taxa').fillna(0)

        # Ordena os cohorts e os dias
        heatmap_data = heatmap_data.sort_index(ascending=False)
        heatmap_data = heatmap_data[sorted(heatmap_data.columns)]

        # Gera o heatmap com Plotly
        fig = px.imshow(
            heatmap_data,
            labels=dict(
                x=f"Dias até {evento_escolhido.lower()}",
                y="Data de entrada (cohort)",
                color="Conversão (%)"
            ),
            color_continuous_scale="Cividis",
            aspect="auto",
            text_auto=".1f"
        )

        fig.update_layout(
            title=f"Cohort por {evento_escolhido}",
            title_font_size=22,
            height=600,
            font=dict(size=22),
            xaxis=dict(
                title=f"Dias até {evento_escolhido.lower()}",
                title_font=dict(size=16),
                tickfont=dict(size=12)
            ),
            yaxis=dict(
                title="Data de entrada (cohort)",
                title_font=dict(size=16),
                tickfont=dict(size=12)
            ),
            coloraxis_colorbar=dict(
                title="Conversão (%)",
                titlefont=dict(size=14),
                tickfont=dict(size=12),
                ticksuffix="%"
            )
        )

        st.plotly_chart(fig, use_container_width=True)
            

    with st.expander("Custo de Aquisição por Convênio"):
        top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=10, step=1, key='key2')
        gasto_convenios = df_gasto.groupby(['Convênio', 'Produto'])['Valor Gasto'].sum().reset_index(name='gasto_total')
        clientes_convenio = df_filtrado.groupby(['convenio_acronimo', 'produto']).size().reset_index(name='clientes')

        gasto_convenios.rename(columns={
            'Convênio': 'convenio_acronimo',
            'Produto': 'produto',
        }, inplace=True)

        convenios_cac = pd.merge(
            gasto_convenios,
            clientes_convenio,
            on=['convenio_acronimo', 'produto'],
            how='outer'
        )

        # Preenche valores ausentes com 0
        convenios_cac[['gasto_total', 'clientes']] = convenios_cac[['gasto_total', 'clientes']].fillna(0)

        # Evita divisão por zero
        convenios_cac = convenios_cac[convenios_cac['clientes'] > 0]

        # Calcula CAC
        convenios_cac['CAC'] = convenios_cac['gasto_total'] / convenios_cac['clientes']

        # Ordena pelos maiores CACs ou maiores volumes, como preferir
        convenios_cac = convenios_cac.sort_values(by='clientes', ascending=False).head(top_n)

        convenios_cac['conv_prod'] = convenios_cac['convenio_acronimo'] + ' - ' + convenios_cac['produto']

        # Gráfico de barras
        fig = px.bar(
            convenios_cac,
            x='CAC',
            y='conv_prod',
            orientation='h',
            text='CAC',
            labels={'CAC': 'CAC (R$)', 'conv_prod': 'Convênio - Produto'}
        )

        fig.update_traces(
            texttemplate='R$ %{text:.2f}',
            textposition='outside'
        )

        fig.update_layout(
            title="CAC por Convênio e Produto",
            height=800,
            xaxis_title="CAC (R$)",
            yaxis_title="",
            font=dict(size=14),
            xaxis_tickprefix='R$ '
        )

        st.plotly_chart(fig, use_container_width=True)


    with st.expander("ROI por Convênio e Produto"):
        top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=10, step=1, key='key_roi')

        # Agrupamentos
        gasto_convenios = df_gasto.groupby(['Convênio', 'Produto'])['Valor Gasto'].sum().reset_index(name='gasto_total')
        comissao_convenios = df_filtrado.loc[df_filtrado['etapa'] == 'PAGO'].groupby(['convenio_acronimo', 'produto'])['comissao_gerada'].sum().reset_index(name='comissao_gerada')

        # Renomeia pra padronizar
        gasto_convenios.rename(columns={
            'Convênio': 'convenio_acronimo',
            'Produto': 'produto',
        }, inplace=True)

        # Merge dos dados
        convenios_roi = pd.merge(
            gasto_convenios,
            comissao_convenios,
            on=['convenio_acronimo', 'produto'],
            how='outer'
        )

        # Preenche faltantes com 0
        convenios_roi[['gasto_total', 'comissao_gerada']] = convenios_roi[['gasto_total', 'comissao_gerada']].fillna(0)

        # Filtra os com gasto > 0 pra evitar divisão por zero
        convenios_roi = convenios_roi[convenios_roi['gasto_total'] > 0]

        # Calcula ROI
        convenios_roi['ROI (%)'] = ((convenios_roi['comissao_gerada'] - convenios_roi['gasto_total']) / convenios_roi['gasto_total']) * 100

        # Ordena pelos maiores ROIs ou conforme necessidade
        convenios_roi = convenios_roi.sort_values(by='ROI (%)', ascending=False).head(top_n)

        # Cria label para gráfico
        convenios_roi['conv_prod'] = convenios_roi['convenio_acronimo'] + ' - ' + convenios_roi['produto']

        # Gráfico de barras
        fig = px.bar(
            convenios_roi,
            x='ROI (%)',
            y='conv_prod',
            orientation='h',
            text='ROI (%)',
            color='ROI (%)',
            color_continuous_scale='Viridis',
            labels={'ROI (%)': 'ROI (%)', 'conv_prod': 'Convênio - Produto'},
        )

        fig.update_traces(
            texttemplate='%{text:.2f}%',
            textposition='outside'
        )

        fig.update_layout(
            title="ROI por Convênio e Produto",
            height=800,
            xaxis_title="ROI (%)",
            yaxis_title="",
            font=dict(size=14)
        )

        st.plotly_chart(fig, use_container_width=True)

