library(shiny)
library(ggplot2)
library(tidyverse)
library(bayesrules)

vis3_attempts <- function(x) {
  paste0(substr(x, 0, nchar(x)-1), "_attempts")
}

data(basketball, package = "bayesrules")

vis3_data <- basketball[basketball$total_minutes > 0, ]

# Remove "TOT" rows – these are season totals for players who switched teams
# We only want per-team stats, not the aggregated seasonal totals
vis3_data <- vis3_data[vis3_data$team != "TOT", ]

# Some players appear multiple times (different teams). Keep only the last row
# for each player (their final team of the season) to avoid duplicates.
vis3_data <- vis3_data[!duplicated(vis3_data$player_name, fromLast = TRUE), ]

vis3_method_dict = list(
  "Two pointers" = "avg_two_pointers", 
  "Three pointers" = "avg_three_pointers",
  "Free throws" = "avg_free_throws",
  "Field Goal" = "avg_field_goals"
  )

# Remove players that did not attempt score via any of the listed methods
# nevermind this will be allowed, those are valid and complete data after all
# vis3_data <- basketball[rowSums(basketball[vis3_attempts(unname(unlist(vis3_method_dict)))]) != 0,]

vis3_data$all_scores = rowSums(vis3_data[unname(unlist(vis3_method_dict))])
vis3_data$all_score_attempts = rowSums(vis3_data[paste0(vis3_attempts(unname(unlist(vis3_method_dict))))])
vis3_data$all_score_fail = vis3_data$all_score_attempts - vis3_data$all_scores

for (m in vis3_method_dict) {
  vis3_data[paste0(m, "_label")] = 
    apply(vis3_data, 1, FUN = function(player, m) {
      name = player[["player_name"]]
      m_scores = as.double(player[[m]])
      m_attempts = as.double(player[[vis3_attempts(m)]])
      m_fail = m_attempts - m_scores
      all_scores = as.double(player[["all_scores"]])
      all_attempts = as.double(player[["all_score_attempts"]])
      all_fail = all_attempts - all_scores
      
      s = function (n) { format(round(n, 2), nsmall = 2) }
      
      paste0(
        name, "<br>",
        "Success rate:", (m_scores / m_attempts) * 100, "%<br><br>",
        "Successes: ", m_scores, "<br>",
        s((m_scores / all_scores) * 100), "% of all successes<br>",
        s((m_scores / all_attempts) * 100), "% of all attempts<br><br>",
        "Failure: ", m_fail, "<br>",
        s((m_fail / all_fail) * 100), "% of all failures<br>",
        s((m_fail/ all_attempts) * 100), "% of all attempts<br><br>",
        "Total: ", m_attempts, "<br>",
        s((m_attempts / all_attempts) * 100), "% of all attempts"
      )
    }, m)
}

vis3_ui <- function () {
  nav_panel(
    title = "Scoring Methods",        # <-- Change this
    icon  = icon("chart-bar"),       # <-- Pick an icon from fontawesome
layout_sidebar(
  sidebar = sidebar(
    title = "Players by their best scoring methods",
    width = 400,
    
    # Context text 
    p("See how each scoring method is favoured by players"),
    
    hr(),
    
    # Filters
    uiOutput("selectInput"),
    sliderInput(
      inputId = "slice",
      label = "Range of players to show",
      min = 1,
      max = length(vis3_data$player_name),
      value = c(1, 30)),
    
    hr(),
    
    # Explanation of how to read the chart 
    p(strong("How to read this chart:")),
    p("The graph shows the specified scoring attempts of the players in range."),
    p("The lighter color shows all attempts, with the darker color showing the successful attempts overlaid onto it."),
    p("The total length of the bar is the number of attempts, and the visible part of the lighter region is failed attempts."),
    
    hr(),
    
    # Hover tip
    p(em("Hover over a bar to display the success rate, followed by how often does the player use the selected scoring method under success or failure scenarios."))
  ),
  
  # Main content area
  card(
    card_header(uiOutput("plotTitle")),
    card_body(
      plotlyOutput("barPlot")
    )
  ),
  
  card(
    card_header("Key Insight"),
    card_body(
      tags$div(
        tags$ul(
          p("Although top players performs quite well regardless of the scoring methods, it is not without variations, especially between two pointers and three pointers."),
          p("The situations where a field goal can be performed is limited, (particularly, \"slam dunk\"s), but when performed it is likely to succeed.")
          
        )
      )
    )
  )
)
  )
}

# Server
vis3_server <- function(input, output, session) {
  output$barPlot <- renderPlotly({
    # This plot is a stacked bar chart technically implemented as
    # grouped bar chart with one bar guaranteed to be no longer
    # than another bar overlapping the other bar
    
    # sort according to successfully attempts and
    # break ties using all attempts
    
    # If rendering server side, this will initially be empty
    if (!length(input$method)) {
      return() # nope, no graph yet
    }

    proc_data = vis3_data %>%
      arrange(
        desc(!!sym(vis3_method_dict[[input$method]])),
        desc(!!sym(vis3_attempts(vis3_method_dict[[input$method]])))) %>%
      slice(input$slice[1]:input$slice[2])
    
    p_labels <- unlist(proc_data[paste0(vis3_method_dict[[input$method]], "_label")], use.names = FALSE)
    
    # https://stackoverflow.com/questions/40149556/ordering-in-r-plotly-barchart
    # https://stackoverflow.com/questions/71441124/remove-text-which-is-displayed-on-bars-in-plotly-bar-chart
    plot_ly() %>%
      add_bars(
        x = proc_data$player_name,
        y = unlist(proc_data[vis3_attempts(vis3_method_dict[[input$method]])], use.names = FALSE),
        marker = list(color = '#87ceeb'),
        text = p_labels,
        hoverinfo = 'text',
        textposition = "none",
        name = "All"
      ) %>%
      add_bars(
        x = proc_data$player_name,
        y = unlist(proc_data[vis3_method_dict[[input$method]]], use.names = FALSE),
        marker = list(color = '#00688B'),
        text = p_labels,
        hoverinfo = 'text',
        textposition = "none",
        name = "Success"
      ) %>%
      layout(
        barmode = 'overlay', xaxis = list(
        categoryorder = "array",
        categoryarray = unlist(proc_data["player_name"], use.names = FALSE)),
        #title = 'PLACEHOLDER TITLE', # not needed, we show with html
        yaxis = list(title = paste("Mean", tolower(input$method))),
        legend = list(x = 0.85, y = 1.0)
      )
  })

  output$selectInput <- renderUI({
    selectInput(
      inputId = "method",
      label = "Method",
      choices = names(vis3_method_dict)
    )
  })

  output$plotTitle <- renderUI({
    # this one can work with empty hopefully
    paste0("Top players at ", tolower(input$method))
  })
}
