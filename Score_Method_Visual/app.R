library(shiny)
library(ggplot2)
library(tidyverse)

basket <- read.csv("../basketball_processed.csv")

method_dict = list(
  "Two pointers" = "avg_two_pointers", 
  "Three pointers" = "avg_three_pointers",
  "Free throws" = "avg_free_throws",
  "Field Goal" = "avg_field_goals"
  )

ui <- fluidPage(
  # Application title
  titlePanel("Players by Scoring Methods per Game"), # Do not forget to add ","
  # Use a sidebar layout
  sidebarLayout(
    # Sidebar component
    sidebarPanel(
      selectInput(
        inputId = "method",
        label = "Method",
        choices = names(method_dict)
      ),
      sliderInput(
        inputId = "slice",
        label = "Rank range",
        width = "600px",
        min = 1,
        max = length(basket$player_name),
        value = c(1, 5)),
      width = 6),
    # Main panel component
    mainPanel(
      plotOutput("barPlot", height = "800px"), width = 6
    )
  )
)

# Server
server <- function(input, output) {
  output$barPlot <- renderPlot({
    basket %>%
      arrange(desc(!!sym(method_dict[[input$method]]))) %>%
      slice(input$slice[1]:input$slice[2]) %>%
      ggplot() +
      geom_col(
        aes(
          !!sym(method_dict[[input$method]]),
          player_name,
          y = reorder(player_name, !!sym(method_dict[[input$method]]))
        ), fill = "deepskyblue4") +
      xlab(paste("Average", tolower(input$method), "per game")) +
      ylab("Player") +
      ggtitle(
        paste("Top player by", tolower(input$method)),
        subtitle = paste("Now showing player", input$slice[1], "to", input$slice[2])
        )
  })
}

# Run Shiny app
shinyApp(ui, server)

