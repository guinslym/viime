import { vBtn, vListTile } from 'jest-puppeteer-vuetify';
import { uploadDataset } from '../util';


describe('download dataset', () => {
  it('download the selected metabolites', async () => {
    await expect(page).toClickXPath(vBtn('Your Datasets'));

    await uploadDataset('downloadTest');
    await expect(page).toClickXPath(vListTile({ title: 'downloadTest.csv ', content: 'Dataset ready for analysis.' }) + vBtn('View Data'));

    // click transform table
    await expect(page).toClickXPath(vListTile({ title: 'Transform Table' }));

    // change transform to 'log 10'
    await expect(page).toClickXPath("//label[@class='v-label theme--light'][contains(text(), 'Log 10')]");

    // change scale to 'Pareto Scaling'
    await expect(page).toClickXPath("//label[@class='v-label theme--light'][contains(text(), 'Pareto Scaling')]");

    // click analyze table
    await expect(page).toClickXPath(vListTile({ title: 'Analyze Table' }));

    // click ANOVA
    await expect(page).toClickXPath(vListTile({ title: 'ANOVA' }));

    // select some metabolites from ANOVA
    /* eslint prefer-template: "off" */
    await expect(page).toClickXPath("//th[@class='column sortable text-xs-left'][contains(text(), 'C26 - Fol')]" + vBtn({ title: 'Adds the highlighted Metabolites to the selected set' }));
    await expect(page).toClickXPath("//th[@class='column sortable text-xs-left'][contains(text(), 'C26 - Veh')]" + vBtn({ title: 'Adds the highlighted Metabolites to the selected set' }));
    await expect(page).toClickXPath("//th[@class='column sortable text-xs-left'][contains(text(), 'C26.Fol - Veh')]" + vBtn({ title: 'Adds the highlighted Metabolites to the selected set' }));

    // click download data
    await expect(page).toClickXPath(vListTile({ title: 'Download Data' }));
    await expect(page).toClickXPath(vBtn({ content: 'Metabolite List' }));

    // wait for download to complete
    await new Promise((resolve) => setTimeout(resolve, 1000));
  });
  it('transpose and download table', async () => {
    await expect(page).toClickXPath(vBtn('Your Datasets'));

    await uploadDataset('downloadTest');
    await expect(page).toClickXPath(vListTile({ title: 'downloadTest.csv ', content: 'Dataset ready for analysis.' }) + vBtn('View Data'));

    // click transform table
    await expect(page).toClickXPath(vListTile({ title: 'Transform Table' }));

    // change transform to 'log 10'
    await expect(page).toClickXPath("//label[@class='v-label theme--light'][contains(text(), 'Log 10')]");

    // change scale to 'Pareto Scaling'
    await expect(page).toClickXPath("//label[@class='v-label theme--light'][contains(text(), 'Pareto Scaling')]");

    // click analyze table
    await expect(page).toClickXPath(vListTile({ title: 'Analyze Table' }));

    // click ANOVA
    await expect(page).toClickXPath(vListTile({ title: 'ANOVA' }));

    // select some metabolites from ANOVA
    /* eslint prefer-template: "off" */
    await expect(page).toClickXPath("//th[@class='column sortable text-xs-left'][contains(text(), 'C26 - Fol')]" + vBtn({ title: 'Adds the highlighted Metabolites to the selected set' }));

    // click download data
    await expect(page).toClickXPath(vListTile({ title: 'Download Data' }));

    // click 'transpose table'
    await expect(page).toClickXPath("//input[@aria-label='Transpose Table']");
    await expect(page).toClickXPath(vBtn({ content: 'Table' }));

    // wait for download to complete
    await new Promise((resolve) => setTimeout(resolve, 1000));
  });
  it('download sample list', async () => {
    await expect(page).toClickXPath(vBtn('Your Datasets'));

    await uploadDataset('downloadTest');
    await expect(page).toClickXPath(vListTile({ title: 'downloadTest.csv ', content: 'Dataset ready for analysis.' }) + vBtn('View Data'));

    // click transform table
    await expect(page).toClickXPath(vListTile({ title: 'Transform Table' }));

    // change transform to 'log 10'
    await expect(page).toClickXPath("//label[@class='v-label theme--light'][contains(text(), 'Log 10')]");

    // change scale to 'Pareto Scaling'
    await expect(page).toClickXPath("//label[@class='v-label theme--light'][contains(text(), 'Pareto Scaling')]");

    // click analyze table
    await expect(page).toClickXPath(vListTile({ title: 'Analyze Table' }));

    // click ANOVA
    await expect(page).toClickXPath(vListTile({ title: 'ANOVA' }));

    // select some metabolites from ANOVA
    /* eslint prefer-template: "off" */
    await expect(page).toClickXPath("//th[@class='column sortable text-xs-left'][contains(text(), 'C26 - Veh')]" + vBtn({ title: 'Adds the highlighted Metabolites to the selected set' }));
    await expect(page).toClickXPath("//th[@class='column sortable text-xs-left'][contains(text(), 'C26.Fol - Veh')]" + vBtn({ title: 'Adds the highlighted Metabolites to the selected set' }));

    // click download data
    await expect(page).toClickXPath(vListTile({ title: 'Download Data' }));

    // unselect a sample filters
    await expect(page).toClickXPath("//input[@aria-label='Fol (5)']");
    await expect(page).toClickXPath(vBtn({ content: 'Sample List' }));

    // wait for download to complete
    await new Promise((resolve) => setTimeout(resolve, 1000));
  });
});
