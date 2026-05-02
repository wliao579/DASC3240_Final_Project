source("vis1.R")
source("Vis_2.R")
source("vis3.R")
source("vis1_animation.R")

library(bslib)

ui <- page_navbar(
  title = "WNBA 2019 - Moneyball Analysis",
  theme = bs_theme(bootswatch = "flatly"),
  vis1_ui(),
  vis2_ui(),
  vis3_ui(),
  vis_anim_ui()
)

server <- function(input, output, session) {
  vis1_server(input, output, session)
  vis2_server(input, output, session)
  vis3_server(input, output, session)
  vis_anim_server(input, output, session)
}

shinyApp(ui, server)
