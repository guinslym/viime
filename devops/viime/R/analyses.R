
#' wilcoxon_test_z_scores
#'
#' @export
wilcoxon_test_z_scores <- function(measurements, groups) {
  Metab = read.csv(measurements, row.names=1)
  groups = read.csv(groups, row.names=1)

  # take the first column
  Group = as.factor(groups[, 1])


  compute <- function(prefix, groupA, groupB) {
    # create a table for p-values
    result <- data.frame(x=numeric(ncol(Metab)), y=numeric(ncol(Metab)), z=numeric(ncol(Metab)))
    colnames(result) <- paste0(prefix, c("Wilcoxon", "Bonferroni", "Hochberg"))

    # calculate Wilcoxon p-values
    for(i in 1:ncol(Metab)) {
      result.dat <- wilcox.test(Metab[Group == groupA, i], Metab[Group == groupB, i])
      result[i,1] <- as.numeric(gsub("$p.value [1]", "", result.dat[3]))
    }
    # calculate adjusted p-value
    result[,2] <- p.adjust(result[,1], method="bonferroni")
    result[,3] <- p.adjust(result[,1], method="hochberg")

    result
  }

  combinations = combn(levels(Group), 2)
  OUT = data.frame(Metabolite=colnames(Metab))

  if (ncol(combinations) == 1) {
    groupA <- combinations[1, 1]
    groupB <- combinations[2, 1]

    sub = compute("", groupA, groupB)
    OUT = cbind(OUT, sub)
  } else {
    for(j in 1:ncol(combinations)) {
      groupA <- combinations[1, j]
      groupB <- combinations[2, j]

      sub = compute(paste0(groupA, " - ", groupB, " "), groupA, groupB)
      OUT = cbind(OUT, sub)
    }
  }

  OUT
}


#' anova_tukey_adjustment
#'
#' @export
anova_tukey_adjustment <- function(measurements, groups) {
  Metab = read.csv(measurements, row.names=1)
  groups = read.csv(groups, row.names=1)

  # take the first column
  Group = as.factor(groups[, 1])

  library(car) #For Type III ANOVA
  library(emmeans) #For pairwise comparisons https://cran.r-project.org/web/packages/emmeans/vignettes/comparisons.html

  # based on the given R code
  OUT <- NULL
  for (n in colnames(Metab)){
    mod <- lm(Metab[[n]] ~ Group)
    a <- Anova(mod, type="III")
    x1 <- cbind(n,t(a[,"Pr(>F)"] ))

    emm.mod <- emmeans(mod, "Group")
    b <- pairs(emm.mod)
    x2 <- summary(b)$p.value
    x2 <- t(x2)
    colnames(x2) <- summary(b)$contrast

    x <- cbind(x1,x2)
    OUT <- rbind(OUT, x)
    colnames(OUT) <- c("Metabolite", row.names(a), colnames(x2))
    rm(mod,a,b,x1,x2,x)
  }

  OUT
}